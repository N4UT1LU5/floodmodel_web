// import { getFloodzone } from "./modules/api.js";

var mapContainerNodeId = "mapContainer";

var mymap;
var myLayerControl;
var x = 0;
var y = 0;
var h = 1;
var r = 1000;

function initControls() {
  if (mymap) {
    // zoom control as default

    // attribution control - static suffix
    mymap.attributionControl.addAttribution("BO GI II Demo Webapp");

    // scale control
    L.control
      .scale({ maxWidth: 500, metric: true, imperial: false })
      .addTo(mymap);

    // layerControl
    var baseLayers = {};
    var overlayLayers = {};
    myLayerControl = L.control.layers(baseLayers, overlayLayers);
    myLayerControl.addTo(mymap);
  }
}

function initBackgroundLayers() {
  if (mymap && myLayerControl) {
    // specify all background WMS layers
    // only OSM as active layer

    var wmsLayer_topplus = L.tileLayer.wms(
      "http://sgx.geodatenzentrum.de/wms_topplus_web_open?",
      {
        format: "image/png",
        layers: "web",
        attribution: "&copy; Bundesamt für Kartographie und Geod&auml;sie",
      }
    );

    var wmsLayer_osm = L.tileLayer
      .wms("https://maps.heigit.org/osm-wms/service?", {
        format: "image/png",
        layers: "osm_auto:all",
        attribution:
          '&copy; <a href="www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      })
      .addTo(mymap);

    var wmsLayer_dtk = L.tileLayer.wms(
      "https://www.wms.nrw.de/geobasis/wms_nw_dtk?",
      {
        format: "image/png",
        layers: "nw_dtk_sw",
      }
    );

    // add baseLayers to Base Layers in layer control
    myLayerControl.addBaseLayer(wmsLayer_topplus, "TopPlus WMS");
    myLayerControl.addBaseLayer(wmsLayer_osm, "OSM WMS");
    myLayerControl.addBaseLayer(wmsLayer_dtk, "DTK WMS");
  }
}

function initMap() {
  mymap = L.map(mapContainerNodeId).setView([51.461372, 7.2418863], 12);

  initControls();

  initBackgroundLayers();
  initInitialData();

  var popup = L.popup();

  function onMapClick(e) {
    x = parseInt(e.latlng.lat * 100000);
    y = parseInt(e.latlng.lng * 100000);
    popup
      .setLatLng(e.latlng)
      .setContent("You clicked the map at " + e.latlng.toString())
      .openOn(mymap);
  }

  mymap.on("click", onMapClick);
}

function getFloodzone(x, y, r, h) {
  fetch(`http://127.0.0.1:5000/api/createFloodzone?x=${x}&y=${y}&r=${r}&h=${h}`)
    .then((response) => response.json())
    .then((data) => {
      console.log(data.features);
      L.geoJSON(data.features).addTo(mymap);
    });
}

function onDomLoaded() {
  initMap();
}

function sendRequestFloodzone() {
  getFloodzone(x, y, r, h);
}

document.addEventListener("DOMContentLoaded", onDomLoaded);
