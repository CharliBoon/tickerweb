import vtkSTLReader from './Geometry/STLReader.js';
import vtkPLYReader from './Geometry/PLYReader.js';
import vtkDracoReader from './Geometry/DracoReader.js';
import vtkSTLWriter from './Geometry/STLWriter.js';
import vtkPLYWriter from './Geometry/PLYWriter.js';
import vtkGLTFImporter from './Geometry/GLTFImporter.js';

var Geometry = {
  vtkSTLReader,
  vtkPLYReader,
  vtkDracoReader,
  vtkSTLWriter,
  vtkPLYWriter,
  vtkGLTFImporter
};

export { Geometry as default };
