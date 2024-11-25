<template>
  <img alt="Vue logo" src="./assets/logo.png">
  <TickerVTK msg="TickerWeb"/>
</template>

<script>
import TickerVTK from './components/TickerVTK.vue'

export default {
  name: 'App',
  components: {
    TickerVTK
  }
}
</script>

<style>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #2c3e50;
  margin-top: 60px;
}
</style>
