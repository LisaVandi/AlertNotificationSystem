(async function() {
  const mapsContainer = document.getElementById("maps");
  const nodeTypeSelector = document.getElementById("node-type-selector");

  let selectedNodesForEdge = [];
  let isCreatingNode = false;
  let confirmedNodes = new Set(); // nodi confermati dal server
  let selectionEnabled = true;    // blocco selezione nodi/arco

  const images = await fetch("/api/images").then(r => r.json()).then(d => d.images);
  const { node_types: nodeTypes } = await fetch("/api/node-types").then(r => r.json());

  nodeTypes.forEach(type => {
    const opt = document.createElement("option");
    opt.value = type.type;
    opt.text = type.display_name;
    document.getElementById("node-type").append(opt);
  });

  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  const socket = new WebSocket(`${proto}//${location.hostname}:8765`);

  socket.onopen = () => {
    console.log("[DEBUG] WebSocket connesso");
  };

  window.activeMaps = [];

  function getColorByOccupancy(occ, capacity) {
    if (capacity === 0) return "#BDBDBD"; 
    const ratio = occ / capacity;
    if (ratio === 0) return "#4CAF50";
    if (ratio < 0.5) return "#FFC107";
    return "#F44336";
  }

  socket.onmessage = async ({ data }) => {
    const msg = JSON.parse(data);

    if (msg === "refresh" || msg.action === "refresh") {
      refreshAllMaps();
    };

    if (msg.action === "node_created") {
      const { node } = msg;
      const mapObj = window.activeMaps.find(m => m.floor === node.floor_level);
      if (!mapObj) return;

      if (confirmedNodes.has(node.node_id)) return; // nodo già disegnato

      confirmedNodes.add(node.node_id);
      selectionEnabled = true; // riabilita selezione nodi/arco

      // Conversione pixel -> latLng
      const point = L.point(node.x, node.y);
      const latlng = mapObj.map.containerPointToLatLng(point);

      const radius = Math.min(5 + (node.current_occupancy || 0), 20);
      const color = getColorByOccupancy(node.current_occupancy, node.capacity);

      L.circleMarker(latlng, { radius, fillOpacity: 0.9, fillColor: color, color: color })
        .addTo(mapObj.markersLayer)
        .bindTooltip(`Node ${node.node_id} (${node.node_type})`);
    }

    if (msg.action === "edge_created") {
      const { edge } = msg;
      const mapObj = window.activeMaps.find(m => m.floor === edge.floor);
      if (!mapObj) return;

      let exists = false;
      mapObj.arcsLayer.eachLayer(polyline => {
        const latlngs = polyline.getLatLngs();
        if (!latlngs || latlngs.length < 2) return;

        const nodeMap = {};
        mapObj.markersLayer.eachLayer(marker => {
          const tooltip = marker.getTooltip();
          if (!tooltip) return;
          const content = tooltip.getContent();
          const match = content.match(/Node (\d+)/);
          if (!match) return;
          const id = match[1];
          const latlng = marker.getLatLng();
          nodeMap[id] = [latlng.lat, latlng.lng];
        });

        const from = nodeMap[edge.from];
        const to = nodeMap[edge.to];
        if (!from || !to) return;

        const sameLine = latlngs.length === 2 &&
          ((latlngs[0].lat === from[0] && latlngs[0].lng === from[1] &&
            latlngs[1].lat === to[0] && latlngs[1].lng === to[1]) ||
           (latlngs[1].lat === from[0] && latlngs[1].lng === from[1] &&
            latlngs[0].lat === to[0] && latlngs[0].lng === to[1]));
        if (sameLine) exists = true;
      });
      if (exists) return;

      const nodeMap = {};
      mapObj.markersLayer.eachLayer(marker => {
        const tooltip = marker.getTooltip();
        if (!tooltip) return; 
        const content = tooltip.getContent();
        const match = content.match(/Node (\d+)/);
        if (!match) return; 
        const id = match[1];
        const latlng = marker.getLatLng();
        nodeMap[id] = [latlng.lat, latlng.lng];
      });
      const from = nodeMap[edge.from];
      const to = nodeMap[edge.to];
      if (from && to) {
        L.polyline([from, to], { weight: 2, opacity: 0.8, color: "black" })
          .addTo(mapObj.arcsLayer);
      }
    }
  };

  for (let imgName of images) {
    const match = imgName.match(/floor(\d+)/i);
    if (!match) continue;
    
    const floor = +match[1];
    const img = new Image();
    img.src = `/MapViewer/public/img/${imgName}`;
    
    await new Promise(resolve => img.onload = resolve);

    const imageWidth = img.width;
    const imageHeight = img.height;

    function graphUrl(floor, imageFilename) {
      return `/api/map?floor=${floor}&image_filename=${imageFilename}&image_width=${imageWidth}&image_height=${imageHeight}`;
    }

    const graph = await fetch(graphUrl(floor, imgName)).then(r => r.json());

    const container = document.createElement("div");
    container.className = "map-container";
    container.innerHTML = `
      <div class="title">Floor ${floor} — ${imgName}</div>
      <div id="map-${floor}" class="map"></div>
    `;
    mapsContainer.append(container);

    const map = L.map(`map-${floor}`, { crs: L.CRS.Simple, minZoom: -1 });
    const bounds = [[0, 0], [graph.imageHeight, graph.imageWidth]];
    map.fitBounds(bounds);

    L.imageOverlay(`/MapViewer/public/${graph.image}`, bounds).addTo(map);

    const markersLayer = L.layerGroup().addTo(map);
    const arcsLayer = L.layerGroup().addTo(map);

    drawElements(graph, markersLayer, arcsLayer, map, floor);

    map.on("click", (e) => {
      if (isCreatingNode) return;
      isCreatingNode = true;

      const coords = map.latLngToContainerPoint(e.latlng);
      const floorClicked = floor;

      window.clickedNode = {
        x_px: Math.round(coords.x),
        y_px: Math.round(coords.y),
        floor: floorClicked,
        latlng: e.latlng
      };

      nodeTypeSelector.style.display = "block";
      nodeTypeSelector.style.top = e.originalEvent.clientY + "px";
      nodeTypeSelector.style.left = e.originalEvent.clientX + "px";

      setTimeout(() => {
        isCreatingNode = false;
      }, 500);
    });

    window.activeMaps.push({ floor, map, markersLayer, arcsLayer });
  }

  async function refreshAllMaps() {
    for (let obj of window.activeMaps) {
      const graph = await fetch(graphUrl(obj.floor)).then(r => r.json());
      obj.markersLayer.clearLayers();
      obj.arcsLayer.clearLayers();
      drawElements(graph, obj.markersLayer, obj.arcsLayer, obj.map, obj.floor);
    }
  }

  function drawElements(graph, mLayer, aLayer, map, floor) {
    const nodeMap = {};
    graph.nodes.forEach(node => {
      const point = L.point(node.x, node.y);
      const latlng = map.containerPointToLatLng(point);
      nodeMap[node.id] = latlng;

      const color = getColorByOccupancy(node.current_occupancy, node.capacity);
      const radius = Math.min(5 + node.current_occupancy, 20);
      L.circleMarker(latlng, { radius, fillColor: color, color: color, fillOpacity: 0.9 })
        .addTo(mLayer)
        .bindTooltip(`Node ${node.id} (${node.node_type}, Occ: ${node.current_occupancy})`)
        .on("click", (e) => {
          if (!selectionEnabled) {
            alert("Attendi che il nodo sia confermato prima di selezionarlo.");
            return;
          }
          if (!confirmedNodes.has(node.id)) {
            alert("Nodo non ancora confermato dal server, attendere...");
            return;
          }

          selectedNodesForEdge.push({
            id: node.id,
            latlng: latlng,
            floor: floor
          });

          if (selectedNodesForEdge.length === 2) {
            const [a, b] = selectedNodesForEdge;

            if (a.floor !== b.floor) {
              alert("I due nodi devono essere sullo stesso piano.");
              selectedNodesForEdge = [];
              return;
            }
            console.log("[DEBUG] Invio create_edge", a.id, b.id);

            socket.send(JSON.stringify({
              action: "create_edge",
              from: a.id,
              to: b.id,
              floor: a.floor
            }));

            const mapObj = window.activeMaps.find(m => m.floor === a.floor);
            if (mapObj) {
              L.polyline([a.latlng, b.latlng], {
                weight: 2,
                opacity: 0.8,
                color: "black"
              }).addTo(mapObj.arcsLayer);
            }

            selectedNodesForEdge = [];
          }
        });
    });

    graph.arcs.forEach(arc => {
      const from = nodeMap[arc.from], to = nodeMap[arc.to];
      if (from && to) {
        L.polyline([from, to], { weight: 2, opacity: 0.8, color: "black" }).addTo(aLayer);
      }
    });
  }

  window.updateNodeType = async function () {
    if (!window.clickedNode) return;

    const newType = document.getElementById("node-type").value;
    const { x_px, y_px, floor } = window.clickedNode;

    // Disabilita selezione nodi/arco finché nodo non confermato
    selectionEnabled = false;

    socket.send(JSON.stringify({
      action: "new_node",
      x_px,
      y_px,
      floor,
      node_type: newType
    }));

    nodeTypeSelector.style.display = "none";
    window.clickedNode = null;
  };

})();
