const template = `<div class="navbar">
  <!-- add routes and components to index.html -->
  <router-link to="/">Home</router-link>  <!-- will transform in A tag -->
    
  <div class="dropdown">
    <button class="dropbtn">Anisotropy
      <i class="fa fa-caret-down"></i>
    </button>
    <div id="entries_anisotropy" class="dropdown-content">
	<router-link to="/tensor">Tensor</router-link>
    </div>
  </div>  
  
  
  <div class="dropdown">
    <button class="dropbtn">FORC
      <i class="fa fa-caret-down"></i>
    </button>
    <div id="entries_forc" class="dropdown-content">
	<router-link to="/forc">FORC</router-link>
	<!-- <router-link to="/stratigraphy">Stratigraphy</router-link> -->
    </div>
  </div>
</div>
`

export default {
  template,
  data () {return {}},
  methods: {},
  computed: {},
}