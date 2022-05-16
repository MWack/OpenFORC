const template = `
	<p>Process FORC data.</p>
	  <input type="file" id="inputFORC" ref="myFiles" @change="onFilePicked" accept=".frc,.forc" style="display:none"/>
	  <button @click="loadFORCclick()" id="fileSelect">Load table from csv file</button>
	<p>`

let id = 0

export default {
  template,
  data() {
    return {
      newD: 0,
      newI: 0,

    }
  },
  methods: {
	loadFORCclick() {
        document.getElementById("inputFORC").click() // trigger hidden file upload element
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