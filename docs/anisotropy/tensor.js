const template = `
	<p>Here you can calculate the best fitting tensor to given measurements. A reference geometry has to be supplied.</p>
	  <table>
		<tr><th colspan="2">Ref. Direction</th><th></th><th colspan="0">Measurements</th></tr>
	  	<tr><th>D</th><th>I</th><th></th><template v-if="matrix_type==='v'">
		<th>x</th><th>y</th><th>z</th></template><template v-else-if="matrix_type==='s'"><th>s</th></template></tr>
	    <tr v-for="dir in dirs" :key="dir.id">
	      <td><input v-model="dir.D" type="number" min=0 max=360></td>
		  <td><input v-model="dir.I" type="number" min=-90 max=90></td>
		  <td><button style="width:100%" @click="removeDir(dir)">Del Dir</button></td>
		  <template v-if="matrix_type==='v'">
			<td><input v-model="dir.x" type="number"></td>
			<td><input v-model="dir.y" type="number"></td>
			<td><input v-model="dir.z" type="number"></td>
		  </template><template v-else-if="matrix_type==='s'">
		    <td><input v-model="dir.s" type="number"></td>
		  </template>
	    </tr>
		<tr><td style="padding-top: 10px;"><input v-model="newD" type="number" min=0 max=360></td><td><input v-model="newI" type="number" min=-90 max=90></td><td><button style="width:100%" @click="addDir">Add Dir</button></td><td colspan="0"></td></tr>
	  </table>
	  <input type="file" id="inputCSV" ref="myFiles" @change="onFilePicked" accept=".csv,.txt" style="display:none"/>
	  <button @click="loadTableCSVclick()" id="fileSelect">Load table from csv file</button>
	  <button @click="storeTableCSVclick()">Store table to csv file</button>
	  <p>
	  Measurements are 
	  <select name="matrix_type" v-model="matrix_type">
        <option value="v" selected>vectorial</option>
        <option value="s">scalar</option>
      </select>
	  </p>
	  <!-- container to have design matrix and tensor side by side -->
	  <div class="parent">
		  <div class="child">
			<button @click="makeDesignMatrix(dirs, matrix_type)">Calculate Design Matrix</button>
			<div v-html:="design_matrix_table"></div>
			</div>
		  <div class="child">
				<button @click="fitTensor(dirs, matrix_type, tensor_type)">Fit tensor</button> with 
				<select name="tensor_type_s" v-model="tensor_type_s" v-if="matrix_type === 's'">
					<option value="s" selected>scalar</option>
				</select>	
				<select name="tensor_type_v" v-model="tensor_type_v" v-else-if="matrix_type === 'v'">
					<option value="v">vectorial</option>
					<option value="p">projected</option>
					<option value="r" selected>refinement</option>
				</select>
				method.
            <div v-if="!tr===false">
			    <!-- tensor results -->
				<h5>Eigenvalues</h5>
				<p>{{ tr.get('n_eval1').toFixed(2) + ' ' + tr.get('n_eval2').toFixed(2) + ' ' + tr.get('n_eval3').toFixed(2) }}</p>
				<h5>Eigenvectors</h5>
				<table>
					<tr><th></th><th>D</th><th>I</th></tr>
					<tr><th>EV1</th><td>{{ tr.get('D1').toFixed(1) }}</td><td>{{ tr.get('I1').toFixed(1) }}</td></tr>
					<tr><th>EV2</th><td>{{ tr.get('D2').toFixed(1) }}</td><td>{{ tr.get('I2').toFixed(1) }}</td></tr>
					<tr><th>EV3</th><td>{{ tr.get('D3').toFixed(1) }}</td><td>{{ tr.get('I3').toFixed(1) }}</td></tr>
				</table>
				<h5>Tensor</h5>
				<table class="tensor">
					<tr><td>{{ tr.get('s')[0].toFixed(2) }}</td><td>{{ tr.get('s')[3].toFixed(2) }}</td><td>{{ tr.get('s')[5].toFixed(2) }}</td></tr>
					<tr><td>{{ tr.get('s')[3].toFixed(2) }}</td><td>{{ tr.get('s')[1].toFixed(2) }}</td><td>{{ tr.get('s')[4].toFixed(2) }}</td></tr>
					<tr><td>{{ tr.get('s')[5].toFixed(2) }}</td><td>{{ tr.get('s')[4].toFixed(2) }}</td><td>{{ tr.get('s')[2].toFixed(2) }}</td></tr>
				</table>
				<h5>Shape</h5>
				<p>{{ 'P = ' + tr.get('P').toFixed(2) + ', L = ' + tr.get('L').toFixed(2) + ', F = ' + tr.get('F').toFixed(2) + ', T = ' + tr.get('T').toFixed(2) }}</p>
				<div id="plotcontainer">
				<div id="plot"></div>  <!-- plotly ellipsoid will go here -->
				</div>
				<h5>Error estimates</h5>
				<p>{{ 'S0 = ' + tr.get('S0').toFixed(4) + ', SD = ' + tr.get('stddev').toFixed(4) + ', QF = ' + tr.get('QF').toFixed(2) + ', E12 = ' + tr.get('E12').toFixed(4) + ', E23 = ' + tr.get('E23').toFixed(4) + ', E13 = ' + tr.get('E13').toFixed(4)}}</p>
				<p>{{ 'F0 = ' + tr.get('F0').toFixed(2) + ', F12 = ' + tr.get('F12').toFixed(2) + ', F23 = ' + tr.get('F23').toFixed(2) }}</p>
			</div>
			<div v-else>
				<p> no results </p>
			</div>	
		  </div>
	  </div>`

let id = 0

export default {
  template,
  data() {
    return {
      newD: 0,
      newI: 0,
      matrix_type: 'v',
	  tensor_type_v: 'r',
	  tensor_type_s: 's',
      dirs: [
	    // some example data to start with
        { id: id++, D: 45.0, I: 0.0, x: 0.64980774, y: 0.71593508, z:0.00313476, s: 0.96573},
        { id: id++, D: 135.0, I: 0.0, x: -0.6551683, y: 0.72129563, z:-0.02352236, s: 0.97331},
        { id: id++, D: 90.0, I: 45.0, x: 0.01064828, y: 0.70842156, z:0.7444223, s: 1.02732},
        { id: id++, D: 90.0, I: -45.0, x: -0.01600884, y: 0.72880915, z:-0.76480989, s: 1.05614},
        { id: id++, D: 0.0, I: -45.0, x: 0.63915946, y: 0.00751352, z:-0.74128753, s: 0.97612},
        { id: id++, D: 0.0, I: 45.0, x: 0.66581658, y: -0.01287407, z:0.76794465, s: 1.01382}
      ],
      design_matrix_table: "",
	  tr: false, // tensor results
	  plotscript: "", // plotly graph of ellipsoid
    }
  },
  methods: {
    addDir() {
      this.dirs.push({ id: id++, D: this.newD, I: this.newI, x: 0, y: 0, z:0, s: 0})
    },
    removeDir(dir) {
      this.dirs = this.dirs.filter((t) => t !== dir)
    },
	loadTableCSVclick() {
        document.getElementById("inputCSV").click() // trigger hidden file upload element
    },
    onFilePicked( event) {
		const input = event.target;
		const files = input.files;
		//let filename = files[0].name;
		const reader = new FileReader();
		let self = this;
		reader.onload = function (e) {
			const text = e.target.result;
			const dirs = csvToArray(text);
			// important to add new ids to rerender vue component view
			dirs.forEach((val, index) => dirs[index]["id"] = id++);
			self.dirs = dirs; // update dirs property of vue component
		};
        reader.readAsText(files[0]);
	},
	storeTableCSVclick() {
        var a = document.createElement("a");
		let dirs = this.dirs;
		dirs.forEach((val, index) => delete dirs[index]["id"]);  // remove id column
		a.href = window.URL.createObjectURL(new Blob([convertToCSV(dirs)], {type: "text/plain"}));
		a.download = "dirs.csv";
		a.click();
    },
	async makeDesignMatrix(dirs, matrix_type) {
      //console.log(dirs)
	  //console.log(matrix_type)
      
      pyodide.globals.set("dirs", Object.assign({}, dirs));
	  pyodide.globals.set("matrix_type", matrix_type);
	
	  try {
        let output = pyodide.runPython(`
           dm = tf.makeDesignMatrix([[e["D"],e["I"]] for e in dirs.to_py().values()], xyz=(matrix_type=='v'))
           pd.DataFrame(dm).to_html(float_format='%.3f')`
		   );
        this.design_matrix_table = output
      } catch (err) {
          alert( "Calculation of design matrix failed.");
      }
    },
	async fitTensor(dirs, matrix_type, tensor_type) {
		//console.log(dirs)
		//console.log(matrix_type)
		//console.log(tensor_type)
	    
		// clean old plot if needed
		let plotscript = document.getElementById("tensor_plotly_script")
		if( plotscript) {
			plotscript.parentNode.removeChild(plotscript);  // remove previous script
		}
		
		let plotdiv = document.getElementById("plot");
		
		if( plotdiv) {
			let plotparent = plotdiv.parentNode;
			plotparent.removeChild(plotdiv);  // remove previous plot div
			// recreate plotdiv
			plotdiv = document.createElement("div");
			plotdiv.setAttribute("id", "plot");
			plotparent.appendChild(plotdiv);
		}
		
		
		// do python stuff here
		pyodide.globals.set("dirs", Object.assign({}, dirs));
        pyodide.globals.set("matrix_type", matrix_type);
        pyodide.globals.set("tensor_type", tensor_type);
		
		try {
			pyodide.runPython(await (await fetch("anisotropy/tensor_fit.py")).text());
			let tr = pyodide.globals.get('tensor').toJs();
			if (tr.get("T") === undefined) {
				tr.set("T", -999); // do this, so that rendering in template does not cause an exception
			}	
			this.tr = tr;
			//console.log(this.tr);
		} catch (err) {
		  alert( "Calculation of tensor failed.")
          this.tr = false
        }
		
		// do plotly output of ellipsoid
		// need to run tensor fit first - defines global tensor variable in python interpreter
		try {
			pyodide.runPython(await (await fetch("anisotropy/tensor_plotly_ellipsoid.py")).text());
		
			let ps = pyodide.globals.get('ps');
			//console.log(ps);
			plotscript = document.createElement("script");
			plotscript.innerHTML = ps;
			plotscript.setAttribute("id", "tensor_plotly_script"); // set id of script element so that we can find it
			document.body.appendChild(plotscript);
		} catch (err) {
          console.log( "tensor plot failed")
        }
	}
  },
  computed: {
	tensor_type() {
       return this.matrix_type === 'v' ? this.tensor_type_v : this.tensor_type_s 
    }
  }
}


function csvToArray(str, delimiter = ",") {
  str = str.replace(/\r\n/g,"\n");  // convert windows line ends to unix line ends
  const headers = str.slice(0, str.indexOf("\n")).split(delimiter);

  // split remaining test into lines
  const rows = str.slice(str.indexOf("\n") + 1).split("\n");

  // Map the rows
  // split values from each row into an array
  // use headers.reduce to create an object
  // object properties derived from headers:values
  // the object passed as an element of the array
  const arr = rows.map(function (row) {
    const values = row.split(delimiter);
    const el = headers.reduce(function (object, header, index) {
      object[header] = parseFloat(values[index]);
      return object;
    }, {});
    return el;
  });

  // return the array
  return arr;
}

function convertToCSV(arr) {
  const array = [Object.keys(arr[0])].concat(arr)

  return array.map(it => {
    return Object.values(it).toString()
  }).join('\n')
}