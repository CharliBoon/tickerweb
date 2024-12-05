<template>
  <div class="app-container">
    <!-- Navbar -->
    <nav class="navbar">
      <div class="navbar-content">
        <button class="settings-btn" @click="toggleSettings">
          <span class="material-icons">settings</span>
        </button>

        <div class="brand">
          <h1 class="title">I Wannabe Nexus</h1>
          <img src="../assets/logo.png" alt="IMS Logo" class="logo" />
        </div>
      </div>
    </nav>

    <!-- Main Content -->
    <div class="main-content">
      <!-- Sidebar Settings Panel -->
      <transition name="fade">
        <aside v-if="showSettings" class="settings-panel">
          <h3>Settings</h3>
          <table class="settings-table">
            <tbody>
              <tr>
                <td> <span class="me-2">Mines</span></td>
                <td>
                  <select class="form-select" v-model="selectedMine" @change="updateMine">
                    <option v-for="mine in mines" :key="mine.value" :value="mine.value">
                      {{ mine.label }}
                    </option>
                  </select>
                </td>
              </tr>
              <!-- Nodes Section -->
              <tr>
                <td colspan="2">
                  <h5>Nodes</h5>
                </td>
              </tr>
              <tr>
                <td>Representation</td>
                <td>
                  <select class="form-select" :value="node_representation"
                    @change="setNodeRepresentation($event.target.value)">
                    <option value="0">Unscaled</option>
                    <option value="1">Scaled</option>
                  </select>
                </td>
              </tr>
              <!-- Events Section -->
              <tr>
                <td colspan="2">
                  <h5 class="text-primary mt-3 mb-2">Events</h5>
                </td>
              </tr>
              <tr>
                <td> <span class="me-2">{{ formattedTimestamp }}</span></td>
                <td>
                  <input type="range" class="form-range" :min="events_timestamp_min" :max="events_timestamp_max"
                    :value="events_timestamp" @input="setEventTimeStamp($event.target.value)" />
                </td>
              </tr>
              <tr>
                <td class="fw-bold">Opacity</td>
                <td>
                  <input type="range" class="form-range" min="0" max="100" :value="events_opacity"
                    @input="setEventOpacity($event.target.value)" />
                </td>
              </tr>

              <!-- Plan Section -->
              <tr>
                <td colspan="2">
                  <h5 class="text-primary mt-3 mb-2">Plan</h5>
                </td>
              </tr>
              <tr>
                <td class="fw-bold">Opacity</td>
                <td>
                  <input type="range" class="form-range" min="0" max="100" :value="plan_opacity"
                    @input="setPlanOpacity($event.target.value)" />
                </td>
              </tr>
              <tr>
                <td class="fw-bold">Representation</td>
                <td>
                  <select class="form-select" :value="plan_representation"
                    @change="setPlanRepresentation($event.target.value)">
                    <option value="0">Points</option>
                    <option value="1">Wireframe</option>
                  </select>
                </td>
              </tr>

              <!-- Volume Section -->
              <tr>
                <td colspan="2">
                  <h5 class="text-primary mt-3 mb-2">Volume</h5>
                </td>
              </tr>
              <tr>
                <td class="fw-bold">Iso&nbsp;&nbsp;<span class="me-2">{{ Math.round(volume_iso) }} mm/s</span>
                  <!-- Display rounded value --></td>
                <td>

                  <input type="range" class="form-range" :min="volume_min" :max="volume_max" :value="volume_iso"
                    @input="setVolumeIso($event.target.value)" />
                </td>
              </tr>
              <tr>
                <td class="fw-bold">Opacity</td>
                <td>
                  <input type="range" class="form-range" min="0" max="100" :value="volume_opacity"
                    @input="setVolumeOpacity($event.target.value)" />
                </td>
              </tr>
            </tbody>
          </table>
        </aside>
      </transition>

      <!-- Map Container -->
      <section class="map-container">
        <div ref="vtkContainer" class="vtk-container"></div>
      </section>
    </div>
  </div>
</template>

<script>
import axios from 'axios';
import { ref, reactive, unref, onMounted, onBeforeUnmount, watchEffect, watch, computed } from 'vue';
// vtk
import '@kitware/vtk.js/Rendering/Profiles/Geometry'; // geometry rendering for WebGL, WebGPU
import '@kitware/vtk.js/Rendering/Profiles/Glyph';    // vtkGlyph3DMapper
import '@kitware/vtk.js/Rendering/Profiles/Molecule'; // vtkSphereMapper
import vtkFullScreenRenderWindow from '@kitware/vtk.js/Rendering/Misc/FullScreenRenderWindow';
import vtkActor from '@kitware/vtk.js/Rendering/Core/Actor';
import vtkMapper from '@kitware/vtk.js/Rendering/Core/Mapper';
//
import vtkXMLPolyDataReader from '@kitware/vtk.js/IO/XML/XMLPolyDataReader';
import vtkXMLImageDataReader from '@kitware/vtk.js/IO/XML/XMLImageDataReader';
import vtkGlyph3DMapper from '@kitware/vtk.js/Rendering/Core/Glyph3DMapper';
import vtkCubeSource from '@kitware/vtk.js/Filters/Sources/CubeSource';
import vtkSphereMapper from '@kitware/vtk.js/Rendering/Core/SphereMapper';
import vtkImageMarchingCubes from '@kitware/vtk.js/Filters/General/ImageMarchingCubes';
import vtkOutlineFilter from '@kitware/vtk.js/Filters/General/OutlineFilter';
//
import vtkPolyData from '@kitware/vtk.js/Common/DataModel/PolyData';
import vtkPoints from '@kitware/vtk.js/Common/Core/Points';
import vtkCellArray from '@kitware/vtk.js/Common/Core/CellArray'
import vtkLookupTable from '@kitware/vtk.js/Common/Core/LookupTable';
import vtkDataArray from '@kitware/vtk.js/Common/Core/DataArray';


export default {

  setup() {
    const selectedMine = ref('Bambanani'); // Default mine
    const session = reactive({ user: 'user', mine: selectedMine.value });

    let urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has('mine')) {
      selectedMine.value = urlParams.get('mine'); // Update the value of selectedMine
      session.mine = selectedMine.value; // Update session.mine to match selectedMine
    }

    // Update the URL to remove query parameters
    window.history.replaceState({}, document.title, window.location.pathname);


    //const session = {user: 'malcolm', mine:'Bambanani'}

    let nodes = { 'data': [], 'meta': {} } // node data - response getNodes - for table, polydata
    let events = { 'data': [], 'meta': {} } // event data - response getEvents - for table, polydata

    let bounds = null // new Array(6).fill(0.0)

    const vtkContainer = ref(null);
    const context = ref(null);
    const showSettings = ref(false);
    const node_representation = ref(0);
    const events_opacity = ref(50);
    const events_timestamp = ref(0);
    const events_timestamp_min = ref(0);
    const events_timestamp_max = ref(0);
    const plan_opacity = ref(100);
    const plan_representation = ref(1);
    const volume_opacity = ref(15);
    const volume_iso = ref(2500);
    const volume_min = ref(0);
    const volume_max = ref(0);
    const mines = ref([]);
    
  
    const formattedTimestamp = computed(() => {
      if (!events_timestamp.value) return 'Loading...'; // Check if it's defined
      const date = new Date(events_timestamp.value); // Use .value to access the actual value
      const yyyy = date.getFullYear();
      const MM = String(date.getMonth() + 1).padStart(2, '0');
      const dd = String(date.getDate()).padStart(2, '0');
      const HH = String(date.getHours()).padStart(2, '0');
      const mm = String(date.getMinutes()).padStart(2, '0');
      const ss = String(date.getSeconds()).padStart(2, '0');
      return `${yyyy}/${MM}/${dd} ${HH}:${mm}:${ss}`;
    });
    const textEncoder = new TextEncoder();
    const path = 'http://localhost:5000';
    //const path = 'http://192.168.0.2:5000';

    // nodes
    const node_lut = vtkLookupTable.newInstance(); // make custom LUT
    const data = new Uint8Array([0, 255, 0, 255, 255, 165, 80, 255, 255, 0, 0, 255]); // RGBA: green, orange, red
    const table = vtkDataArray.newInstance({ values: data, numberOfComponents: 4 }); // to VTK
    node_lut.setTable(table); // LUT = green, orange, red

    const node_glyph = vtkCubeSource.newInstance();
    const node_mapper = vtkGlyph3DMapper.newInstance();
    const node_actor = vtkActor.newInstance();
    //
    node_mapper.setScalarModeToUsePointData()
    node_mapper.setScalarVisibility(true)
    node_mapper.setScalarRange(1, 3)
    node_mapper.setLookupTable(node_lut)
    node_mapper.setScaleFactor(10.0)
    node_actor.setMapper(node_mapper)
    //node_actor.getProperty().setAmbient(0.5)

    // plan
    const plan_reader = vtkXMLPolyDataReader.newInstance();
    const plan_mapper = vtkMapper.newInstance();
    const plan_actor = vtkActor.newInstance();
    //
    plan_mapper.setInputConnection(plan_reader.getOutputPort());
    plan_actor.setMapper(plan_mapper)
    plan_actor.getProperty().setOpacity(0.25)
    plan_actor.getProperty().setColor(0.5, 0.5, 0.5)

    // volume
    const volume_reader = vtkXMLImageDataReader.newInstance();
    const volume_mapper = vtkMapper.newInstance();
    const volume_actor = vtkActor.newInstance();
    //
    const volume_surface = vtkImageMarchingCubes.newInstance({
      contourValue: 2500.0,
      computeNormals: false,
      mergePoints: false,
    });
    //volume_mapper.setInputConnection(volume_reader.getOutputPort());
    volume_surface.setInputConnection(volume_reader.getOutputPort())
    volume_mapper.setInputConnection(volume_surface.getOutputPort());
    volume_actor.setMapper(volume_mapper)
    //volume_actor.getProperty().setOpacity(0.25)
    //volume_actor.getProperty().setRepresentationToWireframe()
    volume_actor.getProperty().setColor(0.5, 1.0, 1.0)

    const outline = vtkOutlineFilter.newInstance()
    const outline_mapper = vtkMapper.newInstance();
    const outline_actor = vtkActor.newInstance();

    outline.setInputConnection(volume_reader.getOutputPort())
    outline_mapper.setInputConnection(outline.getOutputPort());
    outline_actor.setMapper(outline_mapper)
    outline_actor.getProperty().setColor(0.0, 0.0, 0.0)


    // events
    const events_reader = vtkXMLPolyDataReader.newInstance();
    const events_mapper = vtkSphereMapper.newInstance();
    const events_actor = vtkActor.newInstance();
    //
    events_mapper.setInputConnection(events_reader.getOutputPort())
    events_mapper.setScaleFactor(100.0);
    events_mapper.setScaleArray('scale');
    events_mapper.setScalarVisibility(true);
    events_mapper.setScalarModeToUsePointData()
    events_actor.setMapper(events_mapper)
    events_actor.getProperty().setOpacity(0.5)

    function toggleSettings() {
      this.showSettings = !this.showSettings;
    }

    function setNodeRepresentation(rep) {
      node_representation.value = Number(rep);
    }

    function setEventOpacity(opacity) {
      events_opacity.value = Number(opacity);
    }

    function setEventTimeStamp(res) {
      events_timestamp.value = Number(res);
    }

    function setPlanOpacity(opacity) {
      plan_opacity.value = Number(opacity);
    }

    function setPlanRepresentation(rep) {
      plan_representation.value = Number(rep);
    }

    async function onEventFilter(timestamp) {
      const { renderWindow } = context.value
      filterEventData(timestamp)
      renderWindow.render()
    }

    function setVolumeOpacity(opacity) {
      volume_opacity.value = Number(opacity);
    }

    function setVolumeIso(iso) {
      volume_iso.value = Number(iso);
    }

    async function onVolumeIso(iso_value) {
      const { renderWindow } = context.value
      volume_surface.setContourValue(iso_value)
      renderWindow.render()
    }

    async function fetchMines() {
    try {
      const response = await fetch(path + '/mines');
      if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
      const data = await response.json();
      mines.value = data.map((mine) => ({
        value: mine.id || mine,
        label: mine.name || mine,
      }));
    } catch (error) {
      console.error('Error fetching mines:', error);
    }
  }

  // Watch for changes in selectedMine and trigger updates
  watch(selectedMine, async (newMine) => {
    session.mine = newMine; // Update session with new mine
    console.log(`Mine changed to: ${newMine}`);
    await getAllAndRender(); // Re-fetch and re-render data for the new mine
  });



    // provide data to vtk pipelines ------------------------------------------

    // nodes

    function getNodes(args = {}) {
      return new Promise((resolve, reject) => {
        axios.put(path + '/nodes', args)
          .then((response_get) => {
            nodes = response_get.data
            const pd = newPolyDataFromNodes(nodes)
            node_mapper.setInputData(pd, 0)
            node_mapper.setInputData(node_glyph.getOutputData(), 1)
            resolve('nodes_data')
          })
          .catch((error) => {
            reject(error)
          })
      })
    }

    function newPolyDataFromNodes(nodes) {
      const nodes_data = nodes['data']
      const points = vtkPoints.newInstance()
      points.setNumberOfPoints(nodes_data.length)
      const arr_alerts = new Float32Array(nodes_data.length)
      const arr_verts = []

      nodes_data.forEach((node, index) => {
        arr_alerts[index] = node.alert
        arr_verts.push(1, index)
        points.setPoint(index, node.x, node.y, node.z);
      })
      const alerts = vtkDataArray.newInstance({
        numberOfComponents: 1,
        values: arr_alerts,
        name: 'alerts',
      })
      const verts = vtkCellArray.newInstance({ values: Uint16Array.from(arr_verts) })
      const pd = vtkPolyData.newInstance()
      pd.setPoints(points)
      pd.setVerts(verts)
      pd.getPointData().setScalars(alerts)
      return pd
    }

    // plan

    function getPlan(args = {}) {
      return new Promise((resolve, reject) => {
        axios.put(path + '/plan_vtk', args)
          .then((response_get) => {
            plan_reader.parseAsArrayBuffer(textEncoder.encode(response_get.data))
            resolve('plan')
          })
          .catch((error) => {
            reject(error)
          })
      })
    }

    // volume

    function getVolume(args = {}) {
      return new Promise((resolve, reject) => {
        axios.put(path + '/volume_vtk', args)
          .then((response_get) => {
            volume_reader.parseAsArrayBuffer(textEncoder.encode(response_get.data))
            resolve('volume')
          })
          .catch((error) => {
            reject(error)
          })
      })
    }

    // events

    function getEvents(args = {}) {
      return new Promise((resolve, reject) => {
        axios.put(path + '/events', args)
          .then((response_get) => {
            events = response_get.data
            const pd = newPolyDataFromEvents(events)
            events_mapper.setInputData(pd)
            resolve('events_data')
          })
          .catch((error) => {
            reject(error)
          })
      })
    }

    function filterEventData(timestamp) {
      const events_data = events.data.filter((event) => {
        return event.timestamp > timestamp
      }
      )
      const pd = newPolyDataFromEvents({ 'meta': events.meta, 'data': events_data })
      events_mapper.setInputData(pd)
    }

    function newPolyDataFromEvents(events) {
      const events_data = events.data
      const points = vtkPoints.newInstance()
      points.setNumberOfPoints(events_data.length)
      const arr_mags = new Float32Array(events_data.length)
      const arr_timestamp = new Float32Array(events_data.length)
      const arr_scale = new Float32Array(events_data.length)
      const arr_verts = []

      const offset = 1.0
      const min_mag = events['meta'].min_mag
      const max_mag = events['meta'].max_mag

      events_data.forEach((event_data, index) => {
        arr_mags[index] = event_data.mag
        arr_scale[index] = (offset - min_mag + event_data.mag) / (offset - min_mag + max_mag)
        arr_timestamp[index] = event_data.timestamp
        arr_verts.push(1, index)
        points.setPoint(index, event_data.x, event_data.y, event_data.z);
      })
      const mags = vtkDataArray.newInstance({
        numberOfComponents: 1,
        values: arr_mags,
        name: 'mags',
      })
      const scale = vtkDataArray.newInstance({
        numberOfComponents: 1,
        values: arr_scale,
        name: 'scale',
      })
      const timestamp = vtkDataArray.newInstance({
        numberOfComponents: 1,
        values: arr_timestamp,
        name: 'timestamp',
      })
      const verts = vtkCellArray.newInstance({ values: Uint16Array.from(arr_verts) })
      const pd = vtkPolyData.newInstance()
      pd.setPoints(points)
      pd.setVerts(verts)
      pd.getPointData().addArray(mags)
      pd.getPointData().addArray(scale)
      pd.getPointData().addArray(timestamp)
      pd.getPointData().setActiveAttributeByName('timestamp', 0) // scalars
      return pd
    }

    // all --------------------------------------------------------------------

    async function getAllAndRender() {
      const { renderWindow, renderer } = context.value
      await getNodes({ mine: session.mine })
      console.log('nodes nPts: ' + String(node_mapper.getInputData().getNumberOfPoints()))
      if (node_mapper.getInputData().getNumberOfPoints() > 0) {
        bounds = node_mapper.getInputData().getBounds()
        //console.log('nodes nPts: ' + String(node_mapper.getInputData().getNumberOfPoints()))
        console.log(bounds)
        const buffer = 1000.0
        bounds[0] -= buffer
        bounds[1] += buffer
        bounds[2] -= buffer
        bounds[3] += buffer
        bounds[4] -= buffer
        bounds[5] += buffer
      } else {
        bounds = null
      }
      await getVolume({ mine: session.mine })
      if (outline_mapper.getInputData().getNumberOfPoints() > 0 && node_mapper.getInputData().getNumberOfPoints() === 0) {
        bounds = outline_mapper.getInputData().getBounds()
        //console.log('nodes nPts: ' + String(node_mapper.getInputData().getNumberOfPoints()))
        console.log(bounds)
        const buffer = 1000.0
        bounds[0] -= buffer
        bounds[1] += buffer
        bounds[2] -= buffer
        bounds[3] += buffer
        bounds[4] -= buffer
        bounds[5] += buffer
      }
      //
      //Promise.allSettled([getPlan({bounds: bounds, mine: session.mine}), getEvents({bounds: bounds, mine: session.mine, timestamp: 0.0}), getVolume({mine: session.mine})]).then(() => {
      Promise.allSettled([getPlan({ bounds: bounds, mine: session.mine }), getEvents({ bounds: bounds, mine: session.mine, timestamp: 0.0 })]).then(() => {
        const range = events_mapper.getInputData().getPointData().getScalars().getRange()
        events_timestamp_min.value = range[0]
        events_timestamp_max.value = range[1]
        events_timestamp.value = range[0]
        events_mapper.setScalarRange(range)
        //
        const volume_range = volume_reader.getOutputData().getPointData().getScalars().getRange()
        volume_min.value = volume_range[0]
        volume_max.value = volume_range[1]
        volume_iso.value = (volume_range[0] + volume_range[1]) / 2
        volume_mapper.setScalarRange(volume_range)

        renderer.resetCamera()

        const camera = renderer.getActiveCamera();

        // Reduce the field of view to zoom in
        const currentFoV = camera.getViewAngle();
        const newFoV = currentFoV * 0.2;  // Decrease FoV to zoom in (you can adjust this factor)

        camera.setViewAngle(newFoV);
        renderWindow.render()
      })
    }

    function checkModified() {
      return new Promise((resolve, reject) => {
        axios.put(path + '/modified', { mine: session.mine })
          .then((response_get) => {
            console.log(response_get.data)
            resolve('plan')
          })
          .catch((error) => {
            reject(error)
          })
      })
    }


    watch(events_timestamp, (newValue) => {
      onEventFilter(newValue)
    })

    watch(volume_iso, (newValue) => {
      onVolumeIso(newValue)
    })

    watchEffect(() => {
      if (context.value) {
        const { renderWindow } = context.value;
        console.log(unref(node_representation))
        node_mapper.setScaleMode(unref(node_representation));
        node_mapper.update()
        plan_actor.getProperty().setOpacity(unref(plan_opacity) * 0.01);
        plan_actor.getProperty().setRepresentation(unref(plan_representation))
        events_actor.getProperty().setOpacity(unref(events_opacity) * 0.01)
        volume_actor.getProperty().setOpacity(unref(volume_opacity) * 0.01)
        renderWindow.render();
      }
    });

    onMounted(() => {
      console.log('onMounted');

      fetchMines();

      if (!context.value) {
        const fullScreenRenderer = vtkFullScreenRenderWindow.newInstance({
          rootContainer: vtkContainer.value,
          containerStyle: {
            position: 'relative',
            width: '100%',
            height: '100%',
          },
        });

        const renderer = fullScreenRenderer.getRenderer();
        const renderWindow = fullScreenRenderer.getRenderWindow();

        // Set background and enable depth 
        renderer.setBackground(1.0, 1.0, 1.0);
        renderer.setUseDepthPeeling(false);
        renderer.setMaximumNumberOfPeels(100);
        renderer.setOcclusionRatio(0.01);
        renderer.setInteractive(true);

        // Add actors
        renderer.addActor(node_actor);
        renderer.addActor(plan_actor);
        renderer.addActor(events_actor);
        renderer.addActor(volume_actor);
        renderer.addActor(outline_actor);

        // Store context for later access
        context.value = {
          fullScreenRenderer,
          renderWindow,
          renderer,
          node_actor,
          node_mapper,
          node_glyph,
          events_actor,
          events_mapper,
          plan_reader,
          plan_mapper,
          plan_actor,
          volume_reader,
          volume_surface,
          volume_mapper,
          volume_actor,
          outline,
          outline_mapper,
          outline_actor,
        };

        renderWindow.render();

        // Render all and start monitoring for changes
        getAllAndRender();

        // Start the interval for checking modifications
        context.value.checkModifiedInterval = setInterval(checkModified, 30000);
      }
    });

    onBeforeUnmount(() => {
      if (context.value) {
        const { renderer, renderWindow, fullScreenRenderer, node_actor, node_mapper, node_glyph, plan_reader, plan_actor, plan_mapper, events_actor, events_mapper, volume_reader, volume_mapper, volume_actor } = context.value;
        renderer.removeAllActors()
        plan_actor.delete();
        plan_mapper.delete();
        plan_reader.delete();
        node_actor.delete();
        node_mapper.delete();
        node_glyph.delete();
        events_actor.delete();
        events_mapper.delete();
        volume_actor.delete();
        volume_mapper.delete();
        volume_reader.delete();
        volume_surface.delete();
        //
        renderer.delete()
        renderWindow.delete()
        //
        fullScreenRenderer.delete();
        context.value = null;
      }
    });

    return {
      vtkContainer,
      showSettings,
      toggleSettings,
      setNodeRepresentation,
      setEventOpacity,
      setEventTimeStamp,
      setPlanOpacity,
      setPlanRepresentation,
      plan_opacity,
      plan_representation,
      events_timestamp,
      events_timestamp_min,
      events_timestamp_max,
      events_opacity,
      node_representation,
      volume_opacity,
      setVolumeOpacity,
      volume_iso,
      volume_min,
      volume_max,
      setVolumeIso,
      formattedTimestamp,
      mines,
      selectedMine,
    };
  },
}
</script>

<style>
:root {
  --primary-color: #0056b3;
  --secondary-color: #f8f9fa;
  --text-color: #212529;
  --shadow-color: rgba(0, 0, 0, 0.1);
}

body {
  margin: 0;
  font-family: 'Arial', sans-serif;
  color: var(--text-color);
}

/* App Container */
.app-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

/* Navbar Styles */
.navbar {
  background-color: var(--secondary-color);
  box-shadow: 0 2px 4px var(--shadow-color);
  padding: 0 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 60px;
  position: sticky;
  top: 0;
  z-index: 1000;
}

.navbar-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.brand {
  display: flex;
  align-items: center;
  gap: 15px;
  margin-left: auto;
  /* Push to the right */
}

.logo {
  height: 40px;
}

.title {
  font-size: 1.5rem;
  font-weight: bold;
  color: var(--primary-color);
  margin: 0;
}

.settings-btn {
  background-color: var(--primary-color);
  color: white;
  border: none;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  display: flex;
  justify-content: center;
  align-items: center;
  cursor: pointer;
  box-shadow: 0 2px 4px var(--shadow-color);
  transition: transform 0.2s;
}

.settings-btn:hover {
  transform: scale(1.1);
  margin-right: auto;
  /* Push to the left */
}

.material-icons {
  font-size: 24px;
  /* Adjust the icon size if needed */
}

/* Main Content Styles */
.main-content {
  display: flex;
  flex-grow: 1;
  overflow: hidden;
  position: relative;
  /* Ensure child elements are positioned relative to this container */
}

/* Settings Panel Styles */
.settings-panel {
  position: absolute;
  /* Make it overlay on the map */
  top: 20px;
  left: 20px;
  width: auto;
  height: calc(100% - 60px);
  /* Full height minus navbar */
  background-color: var(--secondary-color);
  padding: 20px;
  box-shadow: 2px 0 5px var(--shadow-color);
  overflow-y: auto;
  z-index: 1000;
  /* Ensure it appears on top of other elements */
}

.settings-panel h5 {
  margin-bottom: 20px;
  font-size: 1.2rem;
  color: var(--primary-color);
}

.settings-panel h6 {
  margin-top: 20px;
  margin-bottom: 10px;
  color: var(--primary-color);
}

.settings-table {
  width: 100%;
  border-collapse: collapse;
}

.settings-table td {
  padding: 10px 5px;
}

.form-select {
  width: 100%;
  padding: 5px;
  font-size: 1rem;
  border: 1px solid #ced4da;
  border-radius: 5px;
  outline: none;
  transition: border-color 0.2s;
}

.form-select:focus {
  border-color: var(--primary-color);
}

/* Map Container */
.map-container {
  flex-grow: 1;
  position: relative;
}

.vtk-container {
  width: 100%;
  height: 100%;
}

/* Fade Transition */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s;
}

.fade-enter,
.fade-leave-to {
  opacity: 0;
}
</style>
