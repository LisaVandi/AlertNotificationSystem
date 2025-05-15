let activeFloor = null;
const mapsContainer = document.getElementById("maps");  // Assicurati che esista in HTML!
let maps = []; // Array di {floor, map, markersLayer, arcsLayer}

const nodeTypeSelector = document.getElementById("node-type-selector");
const nodeTypeSelect = document.getElementById("node-type");
let currentClickCoords = null;

let isAddingEdge = false;
let selectedNodesForEdge = [];

// Inizializza tipi nodo (chiamare dopo caricamento tipi dal backend)
function initNodeTypes(types) {
  nodeTypeSelect.innerHTML = "";
  types.forEach(t => {
    const opt = document.createElement("option");
    opt.value = t.type;
    opt.text = t.display_name;
    nodeTypeSelect.appendChild(opt);
  });
}

// Mostra selector tipo nodo vicino al click (evita overflow schermo)
function showNodeTypeSelector(clientX, clientY) {
  const margin = 10;
  const selectorWidth = nodeTypeSelector.offsetWidth || 150;
  const selectorHeight = nodeTypeSelector.offsetHeight || 50;
  const winWidth = window.innerWidth;
  const winHeight = window.innerHeight;

  let left = clientX;
  let top = clientY;

  if (left + selectorWidth + margin > winWidth) {
    left = winWidth - selectorWidth - margin;
  }
  if (top + selectorHeight + margin > winHeight) {
    top = winHeight - selectorHeight - margin;
  }

  nodeTypeSelector.style.display = "block";
  nodeTypeSelector.style.top = top + "px";
  nodeTypeSelector.style.left = left + "px";
}

// Nascondi selector
function hideNodeTypeSelector() {
  nodeTypeSelector.style.display = "none";
  currentClickCoords = null;
}

// Colorazione nodi in base occupazione/capacità
function getColorByOccupancy(occ, capacity) {
  if (capacity === 0) return "#BDBDBD"; 
  const ratio = occ / capacity;
  if (ratio === 0) return "#4CAF50";
  if (ratio < 0.5) return "#FFC107";
  return "#F44336";
}

// Aggiunge nodo tramite POST e disegna subito sulla mappa
async function updateNodeType() {
  if (!currentClickCoords) return;

  const selectedType = nodeTypeSelect.value;
  if (!selectedType) {
    alert("Seleziona un tipo di nodo");
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
        node_type: selectedType
      }),
    });

    if (!resp.ok) {
      alert("Errore nella creazione nodo");
      return;
    }
    
    const data = await resp.json();
    const node = data.node;

    const point = L.point(node.x, node.y);
    const latlng = mapObj.map.containerPointToLatLng(point);

    const marker = createNodeMarker(node, latlng, mapObj);
    mapObj.markersLayer.addLayer(marker);

    hideNodeTypeSelector();
  } catch (e) {
    alert("Errore nella creazione nodo: " + e.message);
  }
}

// Crea marker nodo con gestione click per selezione arco
function createNodeMarker(node, latlng, mapObj) {
  // Calcola raggio minimo 6 e massimo 25 in base a current_occupancy
  // Puoi regolare scala e max a piacere
  const baseRadius = 6;
  const maxRadius = 25;
  const occ = node.current_occupancy || 0;
  const cap = node.capacity || 1;
  // proporzione da 0 a 1 (occu / capacity)
  const ratio = Math.min(occ / cap, 1);
  // raggio interpolato lineare
  const radius = baseRadius + ratio * (maxRadius - baseRadius);

  const marker = L.circleMarker(latlng, {
    radius: radius,
    fillColor: getColorByOccupancy(occ, cap),
    color: "#000000",  // bordo nero (modifica se vuoi)
    weight: 2,
    fillOpacity: 0.85,
  });
  marker.bindTooltip(`Node ${node.node_id || node.id} (${node.node_type})\nOccupancy: ${occ}`);

  // ... resto come prima
  marker.on("click", () => {
    if (!isAddingEdge) return;

    selectedNodesForEdge.push({ id: node.node_id || node.id, latlng });

    if (selectedNodesForEdge.length === 2) {
      const [fromNode, toNode] = selectedNodesForEdge;
      if (fromNode.id === toNode.id) {
        alert("Seleziona due nodi diversi");
        selectedNodesForEdge = [];
        return;
      }

      const mapObjLocal = mapObj; // referenza

      fetch("/api/edges", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          from: fromNode.id,
          to: toNode.id,
          floor: activeFloor
        }),
      }).then(resp => {
        if (!resp.ok) throw new Error("Errore creazione arco");

        L.polyline([fromNode.latlng, toNode.latlng], {
          color: "#2196F3",  // esempio blu
          weight: 5,
          dashArray: "5,10", // opzionale tratteggiato
        }).addTo(mapObjLocal.arcsLayer);

        alert("Arco creato con successo");

        selectedNodesForEdge = [];
        isAddingEdge = false;
        document.getElementById("btnAddEdge").textContent = "Aggiungi arco";
      }).catch(err => {
        alert(err.message);
        selectedNodesForEdge = [];
        isAddingEdge = false;
        document.getElementById("btnAddEdge").textContent = "Aggiungi arco";
      });
    }
  });

  return marker;
}

// Listener click su mappa per aggiungere nodo
function addClickListener(mapObj) {
  mapObj.map.on("click", (e) => {
    if (isAddingEdge) return; // blocca inserimento nodo se aggiunta arco attiva

    const containerPoint = e.containerPoint;
    currentClickCoords = {
      x_px: Math.round(containerPoint.x),
      y_px: Math.round(containerPoint.y),
    };
    activeFloor = mapObj.floor;

    showNodeTypeSelector(e.originalEvent.clientX, e.originalEvent.clientY);
  });
}

// // Carica e disegna grafo piano
// async function loadGraph(floor, map, markersLayer, arcsLayer) {
//   const resp = await fetch(`/api/in-memory-graph?floor=${floor}`);
//   if (!resp.ok) {
//     alert("Grafo non trovato per piano " + floor);
//     return;
//   }
//   const data = await resp.json();

//   if (!data.nodes.length && !data.arcs.length) {
//     console.warn(`Nessun dato per piano ${floor}`);
//     return;
//   }

//   markersLayer.clearLayers();
//   arcsLayer.clearLayers();

//   const mapObj = maps.find(m => m.floor === floor);

//   data.nodes.forEach(node => {
//     const point = L.point(node.x, node.y);
//     const latlng = map.containerPointToLatLng(point);

//     const marker = createNodeMarker(node, latlng, mapObj);
//     markersLayer.addLayer(marker);
//   });

//   data.arcs.forEach(arc => {
//     if (!arc.active) return;  

//     const fromNode = data.nodes.find(n => n.id === arc.from);
//     const toNode = data.nodes.find(n => n.id === arc.to);
//     if (!fromNode || !toNode) return;

//     const fromPoint = L.point(fromNode.x, fromNode.y);
//     const toPoint = L.point(toNode.x, toNode.y);

//     const fromLatLng = map.containerPointToLatLng(fromPoint);
//     const toLatLng = map.containerPointToLatLng(toPoint);

//     L.polyline([fromLatLng, toLatLng], {
//       color: "black",
//       weight: 2,
//     }).addTo(arcsLayer);
//   });
// }

async function loadGraph(floor, map, markersLayer, arcsLayer) {
  const resp = await fetch(`/api/in-memory-graph?floor=${floor}`);
  if (!resp.ok) {
    alert("Grafo non trovato per piano " + floor);
    return;
  }
  const data = await resp.json();

  console.log("Dati grafo caricati:", data);  

  if (!data.nodes.length && !data.arcs.length) {
    console.warn(`Nessun dato per piano ${floor}`);
    return;
  }

  markersLayer.clearLayers();
  arcsLayer.clearLayers();

  data.nodes.forEach(node => {
    const point = L.point(node.x, node.y);
    const latlng = map.containerPointToLatLng(point);

    const marker = createNodeMarker(node, latlng, maps.find(m => m.floor === floor));
    markersLayer.addLayer(marker);
  });

  data.arcs.forEach(arc => {
    if (!arc.active) return;
    const fromNode = data.nodes.find(n => n.id === arc.from);
    const toNode = data.nodes.find(n => n.id === arc.to);
    if (!fromNode || !toNode) return;

    const fromPoint = L.point(fromNode.x, fromNode.y);
    const toPoint = L.point(toNode.x, toNode.y);

    const fromLatLng = map.containerPointToLatLng(fromPoint);
    const toLatLng = map.containerPointToLatLng(toPoint);

    L.polyline([fromLatLng, toLatLng], {
      color: "#333333",
      weight: 3,
      opacity: 0.8,
    }).addTo(arcsLayer);
  });
}

function toggleAddEdgeMode() {
  isAddingEdge = !isAddingEdge;
  selectedNodesForEdge = [];
  document.getElementById("btnAddEdge").textContent = isAddingEdge ? "Annulla aggiunta arco" : "Aggiungi arco";
  alert(isAddingEdge ? "Modalità aggiunta arco attivata. Seleziona due nodi." : "Modalità aggiunta arco disattivata.");
}

document.getElementById("btnAddEdge").addEventListener("click", toggleAddEdgeMode);

async function init() {
  console.log("init() start");

  const resp = await fetch("/api/images");
  console.log("fetch /api/images done", resp.ok);
  if (!resp.ok) return alert("Impossibile caricare immagini");
  const { images } = await resp.json();
  console.log("images:", images);

  const nodeTypesResp = await fetch("/api/node-types");
  console.log("fetch /api/node-types done", nodeTypesResp.ok);
  if (!nodeTypesResp.ok) return alert("Impossibile caricare tipi nodi");
  const nodeTypesData = await nodeTypesResp.json();
  initNodeTypes(nodeTypesData.node_types);
  console.log("node types:", nodeTypesData);

  mapsContainer.innerHTML = "";

  const promises = images.map(async (imgName) => {
    const match = imgName.match(/floor(\d+)\.(jpg|jpeg|png)/i);
    if (!match) return;

    const floor = parseInt(match[1], 10);
    const img = new Image();
    img.src = `/static/img/${imgName}`;
    await new Promise((res) => { img.onload = res; img.onerror = res; });

    const imageWidth = img.width || 1024;
    const imageHeight = img.height || 768;

    const container = document.createElement("div");
    container.className = "map-container";
    container.style.marginBottom = "20px";
    container.innerHTML = `
      <div class="title">Floor ${floor} — ${imgName}</div>
      <div id="map-${floor}" style="width: 100%; height: 400px;"></div>
    `;
    mapsContainer.appendChild(container);

    const map = L.map(`map-${floor}`, { crs: L.CRS.Simple, minZoom: -1 });
    const bounds = [[0, 0], [imageHeight, imageWidth]];
    map.fitBounds(bounds);

    L.imageOverlay(`/static/img/${imgName}`, bounds).addTo(map);

    const markersLayer = L.layerGroup().addTo(map);
    const arcsLayer = L.layerGroup().addTo(map);

    await loadGraph(floor, map, markersLayer, arcsLayer);

    const mapObj = { floor, map, markersLayer, arcsLayer };
    maps.push(mapObj);

    addClickListener(mapObj);
  });

  await Promise.all(promises);

  if (maps.length > 0) activeFloor = maps[0].floor;

  document.getElementById("btnUpdateGraph").addEventListener("click", async () => {
    const mapObj = maps.find(m => m.floor === activeFloor);
    if (!mapObj) return alert("Nessun piano selezionato");
    await loadGraph(mapObj.floor, mapObj.map, mapObj.markersLayer, mapObj.arcsLayer);
    alert("Grafo aggiornato con successo");
  });
}

init().catch(err => console.error("Errore in init():", err));


