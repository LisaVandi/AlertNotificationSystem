let activeFloor = null;
const mapsContainer = document.getElementById("maps");
let maps = []; // {floor, map, markersLayer, arcsLayer, imageHeight}

const nodeTypeSelector = document.getElementById("node-type-selector");
const nodeTypeSelect = document.getElementById("node-type");
let currentClickCoords = null;
let isAddingEdge = false;
let selectedNodesForEdge = [];

function initNodeTypes(types) {
  nodeTypeSelect.innerHTML = "";
  types.forEach(t => {
    const opt = document.createElement("option");
    opt.value = t.type;
    opt.text = t.display_name;
    nodeTypeSelect.appendChild(opt);
  });
}

/* ---------- conversione pixel immagine -> latlng Leaflet ---------- */
function imgPxToLatLng(x, y) {
  const mapObj = maps.find(m => m.floor === activeFloor);
  if (!mapObj) return L.latLng(y, x); 
  return L.latLng(mapObj.imageHeight - y, x);
}

/* ---------- node-type selector ---------- */
function showNodeTypeSelector(clientX, clientY) {
  const margin = 10;
  const selectorWidth = nodeTypeSelector.offsetWidth || 150;
  const selectorHeight = nodeTypeSelector.offsetHeight || 50;
  const winWidth = window.innerWidth;
  const winHeight = window.innerHeight;  
  let left = clientX;
  let top = clientY;  

  if (left + selectorWidth + margin > winWidth) 
    left = winWidth - selectorWidth - margin;
  if (top + selectorHeight + margin > winHeight) 
    top = winHeight - selectorHeight - margin;  
  
  nodeTypeSelector.style.display = "block";
  nodeTypeSelector.style.top = `${top}px`;
  nodeTypeSelector.style.left = `${left}px`;
}

function hideNodeTypeSelector() {
  nodeTypeSelector.style.display = "none";
  currentClickCoords = null;
}

/* ---------- colori & marker ---------- */
function getColorByOccupancy(occ, capacity) {
  if (capacity === 0) 
    return "#BDBDBD";
  const ratio = occ / capacity;
  if (ratio === 0) 
    return "#4CAF50";
  if (ratio < 0.5)
    return "#FFC107";
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
  }).bindTooltip(
    `Node ${node.node_id || node.id} (${node.node_type})\nOccupancy: ${occ}`
  );
  
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

      fetch("/api/edges", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          initial_node: fromNode.id,
          final_node: toNode.id,
          floor: activeFloor,
        }),
      })
        .then(resp => {
          if (!resp.ok) throw new Error("Errore creazione arco");

          L.polyline([fromNode.latlng, toNode.latlng], {
            color: "#2196F3",
            weight: 5,
            dashArray: "5,10",
          }).addTo(mapObj.arcsLayer);

          alert("Arco creato con successo");
        })
        .catch(err => alert(err.message))
        .finally(() => {
          selectedNodesForEdge = [];
          isAddingEdge = false;
          document.getElementById("btnAddEdge").textContent = "Aggiungi arco";
        });
    }
  });  
  
  return marker;
}

/* ---------- click mappa: aggiunta nodo ---------- */
function addClickListener(mapObj) {
  mapObj.map.on("click", e => {
    if (isAddingEdge) return;

    const { x, y } = e.containerPoint;
    currentClickCoords = { x_px: Math.round(x), y_px: Math.round(y) };
    activeFloor = mapObj.floor;

    showNodeTypeSelector(e.originalEvent.clientX, e.originalEvent.clientY);
  });
}

/* ---------- POST nodo & disegno immediato ---------- */
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
        node_type: selectedType,
        image_height: mapObj.imageHeight
      }),
    });
    
    if (!resp.ok) {
      alert("Errore nella creazione nodo");
      return;
    }
    
    const data = await resp.json();
    const node = data.node;

    const latlng = imgPxToLatLng(node.x, node.y);
    const marker = createNodeMarker(node, latlng, mapObj);
    mapObj.markersLayer.addLayer(marker);

    hideNodeTypeSelector();
  } catch (e) {
    alert("Errore nella creazione nodo: " + e.message);
  }
}

/* ---------- carica/disegna grafo ---------- */
async function loadGraph(mapObj) {
  const { floor, markersLayer, arcsLayer } = mapObj;  
  
  const resp = await fetch(`/api/in-memory-graph?floor=${floor}`);
  if (!resp.ok) {
    alert(`Grafo non trovato per piano ${floor}`);
    return;
  }
  
  const data = await resp.json();
  
  markersLayer.clearLayers();
  arcsLayer.clearLayers();
  
  /* nodi */
  data.nodes.forEach(node => {
    const latlng = imgPxToLatLng(node.x, node.y);
    const marker = createNodeMarker(node, latlng, mapObj);
    markersLayer.addLayer(marker);
  });
  
  /* archi */
  data.arcs.forEach(arc => {
    if (arc.active === false) return;
    const fromNode = data.nodes.find(n => n.id === arc.from);
    const toNode = data.nodes.find(n => n.id === arc.to);
    if (!fromNode || !toNode) return;
    
    const fromLatLng = imgPxToLatLng(fromNode.x, fromNode.y);
    const toLatLng = imgPxToLatLng(toNode.x, toNode.y);

    L.polyline([fromLatLng, toLatLng], {
      color: "#333333",
      weight: 3,
      opacity: 0.8,
    }).addTo(arcsLayer);
  });
}

/* ---------- toggle modalità arco ---------- */
function toggleAddEdgeMode() {
  isAddingEdge = !isAddingEdge;
  selectedNodesForEdge = [];
  document.getElementById("btnAddEdge").textContent =
    isAddingEdge ? "Annulla aggiunta arco" : "Aggiungi arco";
  alert(
    isAddingEdge
      ? "Modalità aggiunta arco attivata. Seleziona due nodi."
      : "Modalità aggiunta arco disattivata."
  );
}

document.getElementById("btnAddEdge").addEventListener("click", toggleAddEdgeMode);

/* ------------------------------------------------------------- INIT ----------------------------------------------------------- */
async function init() {
  console.log("init() start");

  /* immagini */
  const imgResp = await fetch("/api/images");
  if (!imgResp.ok) return alert("Impossibile caricare immagini");
  const { images } = await imgResp.json();

  /* tipi nodo */
  const ntResp = await fetch("/api/node-types");
  if (!ntResp.ok) return alert("Impossibile caricare tipi nodi");
  const nodeTypesData = await ntResp.json();
  initNodeTypes(nodeTypesData.node_types);

  mapsContainer.innerHTML = "";

  /* carica planimetrie in ordine */
  for (const imgName of images) {
    const match = imgName.match(/floor(\d+)\.(jpg|jpeg|png)/i);
    if (!match) continue;
    const floor = parseInt(match[1], 10);

    /* pre-carico immagine per dimensioni reali */
    const img = new Image();
    img.src = `/static/img/${imgName}`;
    await new Promise(res => { img.onload = res; img.onerror = res; });

    const imageWidth = img.width || 1024;
    const imageHeight = img.height || 768;

    /* contenitore */
    const container = document.createElement("div");
    container.className = "map-container";
    container.style.marginBottom = "40px";

    container.innerHTML = `
      <div class="title">Floor ${floor} — ${imgName}</div>
      <div id="map-${floor}" style="width: 100%; height: 100%;"></div>
    `;

    mapsContainer.appendChild(container);

    const containerWidth = container.clientWidth;
    container.style.height = `${containerWidth * (imageHeight / imageWidth)}px`;

    // Larghezza massima del contenitore
    container.style.maxWidth = "100%";

    /* leaflet */
    const map = L.map(`map-${floor}`, {
      crs: L.CRS.Simple,
      minZoom: 0,
      maxZoom: 0,
      zoomControl: false,
      dragging: false,
      scrollWheelZoom: false,
      doubleClickZoom: false,
      boxZoom: false,
      keyboard: false,
      tap: false,
      touchZoom: false,
    });

    const bounds = L.latLngBounds(
      L.latLng(0, 0),
      L.latLng(imageHeight, imageWidth)
    );
    map.fitBounds(bounds);
    map.setMaxBounds(bounds);
    L.imageOverlay(`/static/img/${imgName}`, bounds).addTo(map);

    const markersLayer = L.layerGroup().addTo(map);
    const arcsLayer = L.layerGroup().addTo(map);

    const mapObj = { floor, map, markersLayer, arcsLayer, imageHeight };
    maps.push(mapObj);

    await loadGraph(mapObj);
    addClickListener(mapObj);

    // Aggiorna altezza container al resize finestra
    window.addEventListener('resize', () => {
      const w = container.clientWidth;
      container.style.height = `${w * (imageHeight / imageWidth)}px`;
      map.invalidateSize();
    });
  }

  if (maps.length > 0) activeFloor = maps[0].floor;

  document.getElementById("btnUpdateGraph").addEventListener("click", async () => {
    const mapObj = maps.find(m => m.floor === activeFloor);
    if (!mapObj) return alert("Nessun piano selezionato");

    try {
      // Forza il ricaricamento del grafo dal database
      const reloadResp = await fetch("/api/reload-graph", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });

      if (!reloadResp.ok) throw new Error("Errore nel ricaricamento del grafo");

      // Ricarica il grafo nella mappa
      await loadGraph(mapObj);
      alert("Grafo aggiornato con successo");
    } catch (err) {
      alert("Errore nell'aggiornamento del grafo: " + err.message);
    }
  });

  document.getElementById("btnCancelNodeType").addEventListener("click", () => {
    hideNodeTypeSelector();
  });
}

init().catch(err => console.error("Errore in init():", err));
