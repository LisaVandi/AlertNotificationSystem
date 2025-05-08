const socket = new WebSocket("ws://localhost:8000/ws/updates");
socket.onmessage = () => location.reload();

async function fetchAvailableImages() {
  const res = await fetch("/api/images");
  const data = await res.json();
  return data.images;
}

async function drawAllMaps() {
  const container = document.getElementById("maps");
  const images = await fetchAvailableImages();

  for (const image of images) {
    const floorMatch = image.match(/floor(\d+)/i);
    const floor = floorMatch ? parseInt(floorMatch[1]) : null;
    if (!floor) continue;

    const response = await fetch(`/MapViewer/public/json/floor${floor}.json`);
    const graphData = await response.json();

    const div = document.createElement("div");
    div.className = "map-container";

    const title = document.createElement("div");
    title.className = "title";
    title.innerText = `Floor ${floor} - ${image}`;
    div.appendChild(title);

    const mapDiv = document.createElement("div");
    mapDiv.id = `map-${floor}`;
    mapDiv.className = "map";
    div.appendChild(mapDiv);

    container.appendChild(div);

    drawGraph(graphData, `map-${floor}`);
  }
}

function drawGraph(data, elementId) {
  const map = L.map(elementId, {
    crs: L.CRS.Simple,
    minZoom: -1
  });

  const bounds = [[0, 0], [data.imageHeight, data.imageWidth]];
  L.imageOverlay(`/MapViewer/public/${data.image}`, bounds).addTo(map);
  map.fitBounds(bounds);

  const nodeMap = {};
  data.nodes.forEach(node => {
    const coord = [node.y, node.x];
    nodeMap[node.id] = coord;
    L.circleMarker(coord, {
      radius: 5,
      color: "green",
      fillOpacity: 0.9
    }).addTo(map).bindTooltip("Node " + node.id);
  });

  data.arcs.forEach(arc => {
    const from = nodeMap[arc.from];
    const to = nodeMap[arc.to];
    if (from && to) {
      L.polyline([from, to], {
        color: "blue",
        weight: 2,
        opacity: 0.8
      }).addTo(map);
    }
  });
}


let socket = new WebSocket("ws://localhost:8765");

socket.onmessage = (event) => {
  if (event.data === "refresh") {
    console.log("Refreshing map after DB update...");
    document.getElementById("maps").innerHTML = "";
    drawAllMaps();
  }
};

drawAllMaps();
