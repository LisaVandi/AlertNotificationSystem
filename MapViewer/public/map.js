(async function() {
  const mapsContainer = document.getElementById("maps");
  const nodeTypeSelector = document.getElementById("node-type-selector");
  let selectedMarker = null;

  const images = await fetch("/api/images").then(r => r.json()).then(d => d.images);
  const { node_types: nodeTypes } = await fetch("/api/node-types").then(r => r.json());

  nodeTypes.forEach(type => {
    const opt = document.createElement("option");
    opt.value = type.type;
    opt.text = type.display_name;
    document.getElementById("node-type").append(opt);
  });

  function graphUrl(floor, imageFilename) {
    return `/api/map?floor=${floor}&image_filename=${imageFilename}&image_width=1024&image_height=768`;
  }

  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  const socket = new WebSocket(`${proto}//${location.hostname}:8765`);
  socket.onmessage = async ({ data }) => {
    if (data === "refresh") refreshAllMaps();
  };

  window.activeMaps = [];
  for (let imgName of images) {
    const match = imgName.match(/floor(\d+)/i);
    if (!match) continue;
    const floor = +match[1];

    // Automatically determine image type and dimensions
    const img = new Image();
    img.src = `/MapViewer/public/img/${imgName}`;
    await new Promise(resolve => {
      img.onload = resolve;
    });

    const imageWidth = img.width;
    const imageHeight = img.height;

    const graph = await fetch(graphUrl(floor, imgName)).then(r => r.json());

    console.log(`nome: ${graph.image}`);

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

    drawElements(graph, markersLayer, arcsLayer, map);

    window.activeMaps.push({ floor, map, markersLayer, arcsLayer });
  }

  async function refreshAllMaps() {
    for (let obj of window.activeMaps) {
      const graph = await fetch(graphUrl(obj.floor)).then(r => r.json());
      obj.markersLayer.clearLayers();
      obj.arcsLayer.clearLayers();
      drawElements(graph, obj.markersLayer, obj.arcsLayer, obj.map);
    }
  }

  function drawElements(graph, mLayer, aLayer, map) {
    const nodeMap = {};
    graph.nodes.forEach(node => {
      const coord = [node.y, node.x];
      nodeMap[node.id] = coord;
      const radius = Math.min(5 + node.current_occupancy, 20);
      L.circleMarker(coord, { radius, fillOpacity: 0.9 })
        .addTo(mLayer)
        .bindTooltip(`Node ${node.id} (${node.node_type}, Occ: ${node.current_occupancy})`)
        // .on("click", () => {
        //   selectedMarker = node.id;
        //   nodeTypeSelector.style.display = "block";
        // });
        .on("click", () => {
          selectedMarker = node.id;
          nodeTypeSelector.style.display = "block";
          nodeTypeSelector.style.top = event.clientY + "px";
          nodeTypeSelector.style.left = event.clientX + "px";
        });
    });
    graph.arcs.forEach(arc => {
      const from = nodeMap[arc.from], to = nodeMap[arc.to];
      if (from && to) {
        L.polyline([from, to], { weight: 2, opacity: 0.8 })
          .addTo(aLayer);
      }
    });
  }

  // window.updateNodeType = async function() {
  //   if (!selectedMarker) return;
  //   const newType = document.getElementById("node-type").value;
  //   await fetch("/api/update-node-type", {
  //     method: "POST",
  //     headers: { "Content-Type": "application/json" },
  //     body: JSON.stringify({ node_id: selectedMarker, node_type: newType })
  //   });
  //   nodeTypeSelector.style.display = "none";
  //   socket.send("refresh");
  // };

  window.updateNodeType = async function () {
  if (!selectedMarker) return;
  const newType = document.getElementById("node_type").value;

  await fetch("/api/update-node-type", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ node_id: selectedMarker, node_type: newType })
  });

  // Nascondi selettore
  nodeTypeSelector.style.display = "none";

  // Invia richiesta di aggiornamento via WebSocket
  socket.send("refresh"); // o puoi usare "node_updated:<id>" se vuoi ottimizzare
};

})();
