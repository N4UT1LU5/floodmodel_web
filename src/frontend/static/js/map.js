var mapContainerNodeId = "mapContainer";

var mymap;
var myLayerControl;

function initControls() {

    if (mymap) {
        // zoom control as default

        // attribution control - static suffix
        mymap.attributionControl.addAttribution("BO GI II Demo Webapp");

        // scale control
        L.control.scale(
            { maxWidth: 500, metric: true, imperial: false }
        ).addTo(mymap);

        // layerControl
        var baseLayers = {};
        var overlayLayers = {};
        myLayerControl = L.control.layers(baseLayers, overlayLayers);
        myLayerControl.addTo(mymap)
    }

}

function initBackgroundLayers() {

    if (mymap && myLayerControl) {
        // specify all background WMS layers
        // only OSM as active layer

        var wmsLayer_topplus = L.tileLayer.wms(
            'http://sgx.geodatenzentrum.de/wms_topplus_web_open?',
            {
                format: 'image/png', layers: 'web',
                attribution: '&copy; Bundesamt für Kartographie und Geod&auml;sie'
            });

        var wmsLayer_osm = L.tileLayer.wms(
            'https://maps.heigit.org/osm-wms/service?',
            {
                format: 'image/png', layers: 'osm_auto:all',
                attribution: '&copy; <a href="www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            })
            .addTo(mymap);

        var wmsLayer_dtk = L.tileLayer.wms(
            'https://www.wms.nrw.de/geobasis/wms_nw_dtk?',
            { format: 'image/png', layers: 'nw_dtk_sw' });

        // add baseLayers to Base Layers in layer control
        myLayerControl.addBaseLayer(wmsLayer_topplus, "TopPlus WMS");
        myLayerControl.addBaseLayer(wmsLayer_osm, "OSM WMS");
        myLayerControl.addBaseLayer(wmsLayer_dtk, "DTK WMS");
    }
}

function initInitialData() {

    if (mymap && myLayerControl) {
        // BO Point
        var marker = L.marker([51.4465482, 7.2675795]).addTo(mymap);
        marker.bindPopup("<b>Hochschule Bochum</b><br><br><img src='./media/HSBO2.jpg' width='150px' height='75px'>");

        // RUB Point
        var marker2 = L.marker([51.4437999, 7.2595865]).addTo(mymap);
        marker2.bindPopup('<b>RUB Audimax</b><br><br><img src="./media/AudiMax_Ruhr-Uni-Bochum_HDR_2_0.jpg" width="150px" height="75px">');

        // BERMUDA Point
        var marker3 = L.marker([51.4758673, 7.2140504]).addTo(mymap);
        marker3.bindPopup("<b>Bermuda Dreieck</b><br><br><img src='./media/Bermuda.jpg' width='150px' height='75px'>");

        myLayerControl.addOverlay(marker, "Hochschule Bochum - Standort");
        myLayerControl.addOverlay(marker2, "RUB Audimax - Standort");
        myLayerControl.addOverlay(marker3, "Bermuda Dreieck - Standort");
    }
}

function initMap() {
    mymap = L.map(mapContainerNodeId).setView([51.461372, 7.2418863], 12);

    initControls();

    initBackgroundLayers();
    initInitialData();
}

function onDomLoaded() {
    initMap();
}

document.addEventListener("DOMContentLoaded", onDomLoaded);