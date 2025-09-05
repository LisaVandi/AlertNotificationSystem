let activeFloor = null;
const mapsContainer = document.getElementById("maps");
let maps = []; 
const nodeTypeSelector = document.getElementById("node-type-selector");
const nodeTypeSelect = document.getElementById("node-type");
let currentClickCoords = null;
let isAddingEdge = false;
let selectedNodesForEdge = [];
let selectedEdge = null;
const PIXELS_PER_FLOOR = 300;

function createUserMarker(user, latlng, mapObj) {
  const userIcon = L.divIcon({
    className: '',  
    html: `
      <div style="
        font-size: 32px;
        line-height: 32px;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.7);
        transform: translate(-50%, -100%);
      ">👤</div>
    `,
    iconSize: [32, 32],      
    iconAnchor: [16, 32]     
  });

  return L.marker(latlng, { icon: userIcon })
          .bindTooltip(`Utente ${user.user_id}`);
}

async function loadUsers(mapObj) {
  try {
    const resp = await fetch("/api/positions"); 
    if (!resp.ok) {
      console.error(`Error loading user positions: HTTP ${resp.status}`);
      return;
    }
    const data = await resp.json();
    const allPositions = data.positions || [];

    mapObj.usersLayer.clearLayers();

    const thisFloor = mapObj.floor;
    const relevant = allPositions.filter(p => {
      if (typeof p.z !== "number") return false;
      const userFloor = Math.floor(p.z / PIXELS_PER_FLOOR);
      return userFloor === thisFloor;
    });
    
    relevant.forEach(user => {
      const x_px = user.x;
      const y_px = user.y;
      const latlng = imgPxToLatLng(x_px, y_px);
      const marker = createUserMarker(user, latlng, mapObj);
      mapObj.usersLayer.addLayer(marker);
    });
  } catch (e) {
    console.error("Exception in loadUsers():", e);
  }
}


function initNodeTypes(types) {
  nodeTypeSelect.innerHTML = "";
  types.forEach(t => {
    const opt = document.createElement("option");
    opt.value = t.type;
    opt.text = t.display_name;
    nodeTypeSelect.appendChild(opt);
  });
}

// Convert image pixels → Leaflet lat/lng
function imgPxToLatLng(x, y) {
  const mapObj = maps.find(m => m.floor === activeFloor);
  if (!mapObj) return L.latLng(y, x);
  return L.latLng(mapObj.imageHeight - y, x);
}

// Conversion Leaflet latlng → image pixels
function latLngToImgPx(lat, lng, imageHeight) {
  return {
    x: Math.round(lng),
    y: Math.round(imageHeight - lat)
  };
}

function showNodeTypeSelector(clientX, clientY) {
  const margin = 10;
  const selectorWidth = nodeTypeSelector.offsetWidth || 150;
  const selectorHeight = nodeTypeSelector.offsetHeight || 50;
  const winWidth = window.innerWidth;
  const winHeight = window.innerHeight;
  let left = clientX;
  let top = clientY;
  if (left + selectorWidth + margin > winWidth) left = winWidth - selectorWidth - margin;
  if (top + selectorHeight + margin > winHeight) top = winHeight - selectorHeight - margin;
  nodeTypeSelector.style.display = "block";
  nodeTypeSelector.style.top = `${top}px`;
  nodeTypeSelector.style.left = `${left}px`;
}

function hideNodeTypeSelector() {
  nodeTypeSelector.style.display = "none";
  currentClickCoords = null;
}

function getColorByOccupancy(occ, capacity) {
  if (capacity === 0) return "#BDBDBD";
  const ratio = occ / capacity;
  if (ratio === 0) return "#4CAF50";
  if (ratio < 0.5) return "#FFC107";
  return "#F44336";
}

function createNodeMarker(node, latlng, mapObj) {
  const baseRadius = 6;
  const maxRadius = 25;
  const occ = node.current_occupancy || 0;
  const cap = node.capacity || 1;
  const ratio = Math.min(occ / cap, 1);
  const radius = baseRadius + ratio * (maxRadius - baseRadius);

  const marker = L.circleMarker(latlng, {
    radius,
    fillColor: getColorByOccupancy(occ, cap),
    color: "#000000",
    weight: 2,
    fillOpacity: 0.85,
  }).bindTooltip(`Node ${node.node_id || node.id} (${node.node_type})\nOccupancy: ${occ}`);

  marker.on("click", () => {
    if (!isAddingEdge) return;
    selectedNodesForEdge.push({ id: node.node_id || node.id, latlng });
    if (selectedNodesForEdge.length === 2) {
      const [fromNode, toNode] = selectedNodesForEdge;
      if (fromNode.id === toNode.id) {
        selectedNodesForEdge = [];
        return;
      }
      fetch("/api/edges", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          initial_node: fromNode.id,
          final_node: toNode.id,
          floor: activeFloor,
        }),
      })
        .then(async resp => {
          if (!resp.ok) throw new Error(`Error creating edge: ${resp.status}`);
          L.polyline([fromNode.latlng, toNode.latlng], {
            color: "#2196F3",
            weight: 5,
            dashArray: "5,10",
          }).addTo(mapObj.arcsLayer);
        })
        .catch(err => {
          alert(err.message);
        })
        .finally(() => {
          selectedNodesForEdge = [];
          isAddingEdge = false;
          document.getElementById("btnAddEdge").textContent = "Add edge";
        });
    }
  });

  return marker;
}

function addClickListener(mapObj) {
  mapObj.map.on("click", e => {
    if (isAddingEdge) return;
    
    const latlng = e.latlng;
    const px = latLngToImgPx(latlng.lat, latlng.lng, mapObj.imageHeight);

    currentClickCoords = { x_px: px.x, y_px: px.y };
    activeFloor = mapObj.floor;

    showNodeTypeSelector(e.originalEvent.clientX, e.originalEvent.clientY);
  });
}

async function updateNodeType() {
  if (!currentClickCoords) return;
  const selectedType = nodeTypeSelect.value;
  if (!selectedType) {
    return;
  }
  const mapObj = maps.find(m => m.floor === activeFloor);
  if (!mapObj) return;
  const { x_px, y_px } = currentClickCoords;
  try {
    const resp = await fetch("/api/nodes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        x_px,
        y_px,
        floor: activeFloor,
        node_type: selectedType,
        image_height: mapObj.imageHeight
      }),
    });
    if (!resp.ok) throw new Error(`Error creating node: ${resp.status}`);
    const data = await resp.json();
    const node = data.node;
    const latlng = imgPxToLatLng(node.x, node.y);
    mapObj.markersLayer.addLayer(createNodeMarker(node, latlng, mapObj));
    hideNodeTypeSelector();
  } catch (e) {
    alert("Error while creating node: " + e.message);
  }
}

async function loadGraph(mapObj) {
  const { floor, markersLayer, arcsLayer, imageFilename, imageWidth, imageHeight } = mapObj;
  
  try {
    const url = `/api/map`
      + `?floor=${floor}`
      + `&image_filename=${encodeURIComponent(imageFilename)}`
      + `&image_width=${imageWidth}`
      + `&image_height=${imageHeight}`;
      
    const resp = await fetch(url, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin"
    });

    if (!resp.ok) {
      console.error(`Errore caricamento grafo piano ${floor}: HTTP ${resp.status}`);
      return;
    }

    const data = await resp.json();

    markersLayer.clearLayers();
    arcsLayer.clearLayers();

    data.nodes.forEach(node => {
      if (Array.isArray(node.floor_level) && node.floor_level.some(f => f === mapObj.floor)) {
        const latlng = L.latLng(mapObj.imageHeight - node.y, node.x);
        markersLayer.addLayer(createNodeMarker(node, latlng, mapObj));
      }
    });

    data.arcs.forEach(arc => {
      if (arc.active === false) return;  

      const from = L.latLng(imageHeight - arc.y1, arc.x1);
      const to = L.latLng(imageHeight - arc.y2, arc.x2);
      
      const polyline = L.polyline([from, to], {
        color: "#333333",
        weight: 3,
        opacity: 0.8,
      }).addTo(arcsLayer);

      polyline.on("click", () => {
        selectedEdge = arc;
        document.getElementById("btnDisableEdge").disabled = false;

        arcsLayer.eachLayer(layer => {
          layer.setStyle({ color: "#333333", weight: 3 });
        })
        polyline.setStyle({ color: "#333333", weight: 5 });
      });

    });
    
  } catch (e) {
    markersLayer.clearLayers();
    arcsLayer.clearLayers();
  }
}

function toggleAddEdgeMode() {
  isAddingEdge = !isAddingEdge;
  selectedNodesForEdge = [];
  const btn = document.getElementById("btnAddEdge");
  btn.textContent = isAddingEdge ? "Cancel add edge" : "Add edge";
}

async function init() {
  // Check if the system is already configured
  const cfgResp = await fetch("/api/configuration-status");
  const { configured } = await cfgResp.json();
  const btnCfg = document.getElementById("btnConfiguration");
  if (configured) {
    // If already configured, hide the button
    btnCfg.style.display = "none";
  } else {
    // Otherwise, keep the button visible
    btnCfg.style.display = "block";
  }

  const images = (await fetch("/api/images").then(r => r.json())).images;
  const nodeTypesData = (await fetch("/api/node-types").then(r => r.json()));
  initNodeTypes(nodeTypesData.node_types);
  mapsContainer.innerHTML = "";
  for (const imageFilename of images) {
    const m = imageFilename.match(/floor(\d+)\.(jpg|jpeg|png)/i);
    if (!m) continue;
    const floor = parseInt(m[1], 10);
    const img = new Image();
    img.src = `/static/img/${imageFilename}`;
    await new Promise(res => { img.onload = res; img.onerror = res; });
    const imageWidth  = img.width;
    const imageHeight = img.height;

    const container = document.createElement("div");
    container.className = "map-container";

    const title = document.createElement("div");
    title.className = "title";
    title.textContent = `Floor ${floor} — ${imageFilename}`;
    container.appendChild(title);

    const wrapper = document.createElement("div");
    wrapper.className = "map-wrapper";
    wrapper.style.aspectRatio = `${imageWidth} / ${imageHeight}`;

    const mapDiv = document.createElement("div");
    mapDiv.id = `map-${floor}`;
    mapDiv.className = "map";
    wrapper.appendChild(mapDiv)

    container.appendChild(wrapper);
    mapsContainer.appendChild(container);

    const map = L.map(`map-${floor}`, {
      crs: L.CRS.Simple,
      minZoom: 0, maxZoom: 0,
      zoomControl: false, dragging: false,
      scrollWheelZoom: false, doubleClickZoom: false,
      boxZoom: false, keyboard: false,
      tap: false, touchZoom: false,
    });
    
    const bounds = L.latLngBounds([imageHeight,0], [0, imageWidth]);
    
    map.fitBounds(bounds);
    map.setMaxBounds(bounds);
    L.imageOverlay(`/static/img/${imageFilename}`, bounds).addTo(map);
    const markersLayer = L.layerGroup().addTo(map);
    const arcsLayer    = L.layerGroup().addTo(map);
    const usersLayer   = L.layerGroup().addTo(map);

    const mapObj = {
      floor,
      map,
      markersLayer,
      arcsLayer,
      usersLayer,
      imageFilename,
      imageWidth,
      imageHeight
    };
    maps.push(mapObj);
    await loadGraph(mapObj);
    await loadUsers(mapObj); 
    addClickListener(mapObj);
    window.addEventListener("resize", () => {
      maps.forEach(({ map, imageWidth, imageHeight }) => {
        const container = document.getElementById(`map-Simple`)?.parentElement;
        if (container) {
          const wrapper = container.querySelector(".map-wrapper");
          wrapper.style.aspectRatio = `${imageWidth} / ${imageHeight}`;
        }
        map.invalidateSize();
      });
    });

  }
  if (maps.length > 0) {
    activeFloor = maps[0].floor;
  }

  const POLLING_INTERVAL_MS = 3000;
  setInterval(() => {
    maps.forEach(mObj => {
      loadUsers(mObj);
    });
  }, POLLING_INTERVAL_MS);

  document.getElementById("btnAddEdge")
    .addEventListener("click", toggleAddEdgeMode);

  document.getElementById("btnDisableEdge").addEventListener("click", async () => {
  if (!selectedEdge) {
    alert("Please select an edge first.");
    return;
  }

  const btn = document.getElementById("btnDisableEdge");
  btn.disabled = true;
  btn.textContent = "Disabling...";

  try {
    const resp = await fetch("/api/disable-edge", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ arc_id: selectedEdge.arc_id }),
    });

    if (!resp.ok) throw new Error(`Error disabling edge: ${resp.status}`);

    alert("Edge disabled successfully.");

    selectedEdge = null;
    btn.textContent = "Disable edge";

    const mapObj = maps.find(m => m.floor === activeFloor);
    if (mapObj) await loadGraph(mapObj);

    btn.disabled = true;
  } catch (err) {
    alert("Failed to disable edge: " + err.message);
    btn.disabled = false;
    btn.textContent = "Disable edge";
  }
});

  document.getElementById("btnUpdateGraph")
    .addEventListener("click", async () => {
      await fetch("/api/reload-graph", { method: "POST" });
      const mapObj = maps.find(m => m.floor === activeFloor);
      if (mapObj) {
        await loadGraph(mapObj);
      }
    });
    
  document.getElementById("btnCancelNodeType")
    .addEventListener("click", hideNodeTypeSelector);

  document.getElementById("btnConfiguration").addEventListener("click", async () => {
    const btn = document.getElementById("btnConfiguration");
    if (!confirm("Are you sure to complete the configuration and start the full system?")) return;
    btn.disabled = true;
    btn.textContent = "Processing...";
    try {
      const resp = await fetch("/api/configuration-completed", { method: "POST" });
      if (!resp.ok) throw new Error("Failed to notify configuration completion");
      alert("Configuration completed! The full system will start shortly.");
      btn.style.display = 'none';  
    } catch (e) {
        alert("Error: " + e.message);
         btn.disabled = false;
        btn.textContent = "Configuration completed";      
      }
    });
  }

init().catch(err => console.error("Error in init():", err));

// const socket = new WebSocket("ws://localhost:8000/ws/positions");

// socket.onopen = () => {
//     console.log("WebSocket connection established");
// };

// socket.onmessage = function(event) {
//     const data = JSON.parse(event.data);
//     const positions = data.positions;
    
//     // Funzione per aggiornare la mappa con le nuove posizioni degli utenti
//     updateMapWithUserPositions(positions);
// };

// socket.onclose = function(event) {
//     console.log("WebSocket connection closed");
// };

// // Funzione per aggiornare la mappa con le posizioni degli utenti
// function updateMapWithUserPositions(positions) {
//     // Per ogni posizione, calcoliamo le coordinate in lat/lng e creiamo un marker
//     positions.forEach(user => {
//         const x_px = user.x;
//         const y_px = user.y;
//         const latlng = imgPxToLatLng(x_px, y_px);
        
//         // Crea un marker per l'utente
//         const marker = createUserMarker(user, latlng);
        
//         // Aggiungi il marker alla mappa
//         maps.forEach(mapObj => {
//             if (mapObj.floor === activeFloor) {
//                 mapObj.usersLayer.clearLayers();  // Rimuovi i vecchi marker
//                 mapObj.usersLayer.addLayer(marker);  // Aggiungi i nuovi marker
//             }
//         });
//     });
// }
