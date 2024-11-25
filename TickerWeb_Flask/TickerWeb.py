import vtk
import csv
import random
import os
import sys
import datetime
import abc
import numpy

# VTK stuff -------------------------------------------------------------------

class vtkGeometryBytestream(abc.ABC):

    def __init__(self):
        self.writer = vtk.vtkXMLPolyDataWriter()
        self.writer.SetWriteToOutputString(True)
        self.writer.SetDataModeToBinary()
        #self.writer.SetDataModeToAscii()
        #self.writer.SetCompressorTypeToNone()
        self.writer.SetCompressorTypeToZLib() # etc.
        
    def Update(self):
        self.writer.Update()
    
    def GetGeometry(self) -> bytes:
        self.writer.Write()
        bytestream = self.writer.GetOutputString()
        return bytestream


# VTK derived source - plans

class vtkPntReader(vtk.vtkProgrammableSource):
    
    def __init__(self):
        super().__init__()
        self.filename = ''
        self.SetExecuteMethod(self._Parse)
        self.bENU = True
        
    def SetFileName(self,_filename: str):
        self.filename = _filename
        self.Modified()
        
    def _Parse(self):
        if self.filename == '':
            return
        #
        newPts = vtk.vtkPoints()
        newLines = vtk.vtkCellArray()
        #
        file = open(self.filename,'r')
        lnCount = 0
        ptCount = 0
        count = 0
        bFirst3 = True
        for line in file.readlines():
            if line[0] == '#':
                if line.strip() == '# CoordinateSystem = SWD':
                    self.bENU = False
                # DistanceUnit = METER
                continue
            xyzs=line.split()
            if self.bENU:
                x=float(xyzs[0])
                y=float(xyzs[1])
                z=-float(xyzs[2])
            else:
                x=-float(xyzs[1])
                y=-float(xyzs[0])
                z=-float(xyzs[2])
            status = int(xyzs[3])
            if (status == 3) and not(bFirst3):
                newLines.InsertNextCell(ptCount)
                for n in range(ptCount):
                    newLines.InsertCellPoint(count)
                    count += 1
                ptCount = 0
            bFirst3 = False
            newPts.InsertNextPoint(x,y,z)
            ptCount += 1
        newLines.InsertNextCell(ptCount)
        for n in range(ptCount):
            newLines.InsertCellPoint(count)
            count += 1
        #
        self.GetPolyDataOutput().SetPoints(newPts)
        self.GetPolyDataOutput().SetLines(newLines)
        del newPts
        del newLines
        
class vtkMultiPntReader(vtk.vtkProgrammableSource):

    def __init__(self):
        super().__init__()
        self.paths = []
        self.SetExecuteMethod(self._Parse)
        self.ext_cache = '.vtp'
        
    def SetPaths(self, paths: list[str]):
        self.paths = paths
        self.Modified()
        
    def _Parse(self):
        vtpReader = vtk.vtkXMLPolyDataReader()
        vtpWriter = vtk.vtkXMLPolyDataWriter()
        vtpWriter.SetDataModeToBinary()
        vtpWriter.SetCompressorTypeToZLib()
        vtkAppend = vtk.vtkAppendPolyData()
        vtkAppend.UserManagedInputsOn()
        vtkAppend.SetNumberOfInputs(2)
        pntReader = vtkPntReader()
        pdAppend = vtk.vtkPolyData()
        for path in self.paths:
            pre, ext = os.path.splitext(path)
            pthCache = pre+self.ext_cache
            if os.path.isfile(pthCache) and (os.path.getmtime(path) <= os.path.getmtime(pthCache)):
                vtpReader.SetFileName(pthCache)
                vtpReader.Update()
                vtkAppend.SetInputDataByNumber(0,pdAppend)
                vtkAppend.SetInputDataByNumber(1,vtpReader.GetOutput())
            else:
                pntReader.SetFileName(path)
                pntReader.Update()
                vtkAppend.SetInputDataByNumber(0,pdAppend)
                vtkAppend.SetInputDataByNumber(1,pntReader.GetPolyDataOutput())
                # cache in vtp format
                vtpWriter.SetInputData(pntReader.GetPolyDataOutput())
                vtpWriter.SetFileName(pthCache)
                vtpWriter.Write()
            vtkAppend.Update()
            pdAppend = vtk.vtkPolyData()
            pdAppend.ShallowCopy(vtkAppend.GetOutput())
        self.GetPolyDataOutput().SetPoints(pdAppend.GetPoints())
        self.GetPolyDataOutput().SetLines(pdAppend.GetLines())

class vtkPlanPipeline(vtkGeometryBytestream):

    def __init__(self):
        super().__init__()
        self.plan_source = vtkMultiPntReader()
        self.box = vtk.vtkBox()        
        self.box.Modified()
        self.clipper = vtk.vtkClipPolyData()
        self.clipper.SetInputConnection(self.plan_source.GetOutputPort())
        self.clipper.SetClipFunction(self.box)
        self.clipper.InsideOutOn()
        self.writer.SetInputConnection(self.clipper.GetOutputPort())
        
    def SetPaths(self, paths: list[str]):
        self.plan_source.SetPaths(paths)
        
    def SetBounds(self, bounds):
        if bounds:
            self.box.SetBounds(bounds)
            self.writer.SetInputConnection(self.clipper.GetOutputPort())
        else:
            self.writer.SetInputConnection(self.plan_source.GetOutputPort())
        
        
class vtkVolumePipeline:

    def __init__(self):
        super().__init__()
        self.writer = vtk.vtkXMLImageDataWriter()
        self.writer.SetWriteToOutputString(True)
        self.writer.SetDataModeToBinary()
        #self.writer.SetDataModeToAscii()
        #self.writer.SetCompressorTypeToNone()
        self.writer.SetCompressorTypeToZLib()
        #
        self.filename = ''
        self.ext_cache = '.vti'
    
    def SetPath(self, filename):
        self.filename = filename
        
    def ReadDP3(self, filename):
        attr = {}
        file = open(filename, 'r')
        all_lines = file.readlines()
        lines = all_lines[:8]
        attr['file'] = lines[0].split()[1]
        attr['axes'] = lines[1].split()[1]
        attr['orig'] = [float(val) for val in lines[2].split()[1:]]
        attr['offs'] = [float(val) for val in lines[3].split()[1:4]]
        attr['dims'] = [int(val) for val in lines[4].split()[1:4]]
        attr['name'] = lines[5].split()[2:]
        attr['form'] = lines[6].split()[2:]
        attr['unit'] = lines[7].split()[2:]

        strAxes = 'ENU'
        if attr['axes'] == 'SWD': # flip
            strAxes = 'SWD'
            dims = attr['dims']
            attr['dims'] = [dims[1], dims[0], dims[2]]
            offs = attr['offs']
            attr['offs'] = [offs[1], offs[0], offs[2]]
            oX, oY, oZ = attr['orig']
            attr['orig'] = [-oY-(attr['dims'][0]*attr['offs'][0]), -oX-(attr['dims'][1]*attr['offs'][1]), -oZ-(attr['dims'][2]*attr['offs'][2])]
            attr['axes'] = 'ENU'

        nVars = len(attr['name'])
        dX, dY, dZ = attr['offs']
        nX, nY, nZ = attr['dims']
        n = nX*nY*nZ
        
        arrays = []
        for name in attr['name']:
            array = vtk.vtkFloatArray()
            array.SetName(name)
            array.SetNumberOfComponents(1)
            array.SetNumberOfTuples(n)
            arrays.append(array)

        a = numpy.empty((nVars, nX, nY, nZ))
        a[:,:,:,:] = numpy.nan # initialize to NaN

        # assign data values from dp3
        for line in all_lines[8:]:
            blocks = line.split()
            iX, iY, iZ = [int(float(val)) for val in blocks[0:3]]
            # dp3 is point coords - convert to index
            iX = int(iX/dX)
            iY = int(iY/dY)
            iZ = int(iZ/dZ)
            # if SWD then x,y already swapped  - now reverse index to position from end x,y,z
            if strAxes == 'SWD':   
                iX = nX-1-iX
                iY = nY-1-iY
                iZ = nZ-1-iZ
            # extract data values
            values = [float(val) for val in blocks[3:3+nVars]]
            for i in range(nVars):
                a[i,iX,iY,iZ] = values[i]
        # VTK ravels z,y,x
        for iZ in range(nZ):
           for iY in range(nY):
                for iX in range(nX):
                    index = (iZ * (nY*nX)) + (iY*(nX)) + iX
                    for i in range(nVars):
                        arrays[i].SetValue(index, a[i,iX,iY,iZ])
        #
        img = vtk.vtkImageData()
        img.SetOrigin(attr['orig'])
        img.SetSpacing(attr['offs'])
        img.SetDimensions(attr['dims'])
        for array in arrays:
            img.GetPointData().AddArray(array)
            del array
        img.GetPointData().SetActiveAttribute(0,0) 
        #
        return img
        
    def GetImage(self) -> bytes:
        pre, ext = os.path.splitext(self.filename)
        pthCache = pre+self.ext_cache
        if os.path.isfile(pthCache) and (os.path.getmtime(self.filename) <= os.path.getmtime(pthCache)):
            ifile = open(pre+'.vti')
            bytestream = ifile.read()
        else:    
            img = self.ReadDP3(self.filename)
            self.writer.SetInputData(img)
            self.writer.Update()    
            self.writer.Write()
            bytestream = self.writer.GetOutputString()
            # cache bytestream
            ofile = open(pthCache, 'w')
            ofile.write(bytestream)
            ofile.close()
        return bytestream
        

# Non VTK stuff ---------------------------------------------------------------

# parse Nodes CSV into dict

class NodeData:

    def __init__(self):
        self.path = ''
        
    def SetPath(self, path: str):
        self.path = path
        
    def GetData(self) -> dict:
        data = []
        meta = {}
        #
        if not os.path.isfile(self.path):
            return {'data':data, 'meta':meta}
        with open(self.path) as csvfile:
            reader = csv.DictReader(csvfile)
            bSWD = ' X (South) [m]' in reader.fieldnames
            for row in reader:
                if bSWD:
                    x=-float(row[' Y (West) [m]'])
                    y=-float(row[' X (South) [m]'])
                    z=-float(row[' Z (Down) [m]'])
                else:
                    x= float(row[' Y (East) [m]'])
                    y= float(row[' X (North) [m]'])
                    z=-float(row[' Z (Down) [m]'])
                
                alert = (min(random.randint(0, 2), random.randint(0, 2), random.randint(0, 2)))+1
                dctData = {'x':x, 'y':y, 'z':z, 'id':float(row['# index']), 'alert':alert}
                data.append(dctData)
        return {'data':data, 'meta':meta}

# parse Events CSV into dict

class EventData:

    def __init__(self):
        self.path = ''
        self.offset = 1.0
        self.minimum = -2.0
        self.bounds = None
        self.timestamp = 0.0
        
    def SetPath(self, path: str):
        self.path = path
        
    def SetBounds(self, bounds: list[float]):
        self.bounds = bounds
        
    def SetTimeStamp(self, timestamp: float):
        self.timestamp = timestamp
        
    def GetData(self) -> dict:
        data = []
        meta = {}
        # 
        min_mag = sys.float_info.max
        max_mag = -sys.float_info.max
        bounds = self.bounds
        if not os.path.isfile(self.path):
            return {'data':data, 'meta':meta}
        with open(self.path) as csvfile:
            count = 0
            reader = csv.DictReader(csvfile)
            bSWD = 'LocS [m]' in reader.fieldnames
            for row in reader:
                if not row['Local Magnitude']:
                    continue
                if float(row['Local Magnitude']) < self.minimum:
                    continue
                if float(row['Local Magnitude']) < min_mag:
                    min_mag = float(row['Local Magnitude'])
                if float(row['Local Magnitude']) > max_mag:
                    max_mag = float(row['Local Magnitude'])
                dt = datetime.datetime.strptime(row['EventTime'], "%Y/%m/%d %H:%M:%S")
                timestamp=datetime.datetime.timestamp(dt)
                
                if self.timestamp:
                    if timestamp < self.timestamp:
                        continue
                
                if bSWD:
                    x=-float(row['LocW [m]'])
                    y=-float(row['LocS [m]'])
                    z=-float(row['##LocD [m]'])
                else:
                    x= float(row['LocE [m]'])
                    y= float(row['LocN [m]'])
                    z=-float(row['##LocD [m]'])
                
                if bounds:
                    if not ((bounds[0] < x < bounds[1] and (bounds[2] < y < bounds[3]) and (bounds[4] < z < bounds[5]))):
                        continue
                                    
                dctData = {'x':x, 'y':y, 'z':z, 'mag':float(row['Local Magnitude']), 'timestamp':timestamp}
                data.append(dctData)
        
        meta = {'min_mag':min_mag, 'max_mag':max_mag, 'thr_mag':self.minimum}
        return {'data':data, 'meta':meta} 
        

# a simple provider, not quite stateless

class DataProvider(abc.ABC):

    def __init__(self):
        pass
        
    @abc.abstractmethod
    def GetMines(self):
        raise NotImplementedError()
        
    @abc.abstractmethod
    def GetNodes(self) -> dict:
        raise NotImplementedError()
        
    @abc.abstractmethod
    def GetPlan(self) -> dict:
        raise NotImplementedError()
        
    @abc.abstractmethod
    def GetEvents(self) -> dict:
        raise NotImplementedError()
        
    @abc.abstractmethod
    def GetVolume(self) -> dict:
        raise NotImplementedError()


class DataProvider_FileSystem(DataProvider): # file-system based provider

    def __init__(self, dirAllData):
        super().__init__()
        self.dirAllData = dirAllData
        self.dctDirs = dict()
        self.dctTypes = {'plan':'*.pnt', 'events':'events.csv', 'nodes':'nodes.csv', 'volume':'volume.dp3'}
        #
        self.node_data = NodeData()
        self.event_data = EventData()
        self.plan_pipeline = vtkPlanPipeline()
        self.volume_pipeline = vtkVolumePipeline()
    
    def SetAllDataFolder(self, dirAllData: str):
        self.dirAllData = dirAllData
        
    def AddMine(self, strMine: str, strSubDir: str):
        dctMine = {'subDir':strSubDir, 'status':{'plan':{'timestamp':0.0, 'modified': False, 'exists':False}, 'nodes':{'timestamp':0.0, 'modified': False, 'exists':False}, 'events':{'timestamp':0.0, 'modified': False, 'exists':False}, 'volume':{'timestamp':0.0, 'modified': False, 'exists':False}}}
        self.dctDirs[strMine] = dctMine
                
    def GetMines(self) -> list[str]:
        return list(self.dctDirs.keys())
    
    def _GetDataDir(self, strMine: str) -> str:
        dirMine = self.dctDirs[strMine]['subDir']
        return self.dirAllData + '\\' + dirMine
        
    def _GetPath(self, strMine: str, strType: str) -> list[str]:
        dirData = self._GetDataDir(strMine)
        dirType = dirData + '\\'+strType
        infType = self.dctTypes[strType]
        name, ext = infType.split('.')
        if name == '*': # wildcard - multiple files
            return [dirType+'\\'+file for file in os.listdir(dirType) if file.endswith('.%s' % ext)]
        else:
            return dirType+'\\'+infType
    
    def GetModified(self, strMine: str) -> list[str]:
        lstModified = []
        lstMissing = [] # will use for warning
        for strType in {'nodes', 'events', 'volume'}:
            exists = os.path.isfile(self._GetPath(strMine, strType))
            self.dctDirs[strMine]['status'][strType]['exists'] = exists
            if not exists:
                lstMissing += strType
                continue
            if (timestamp := os.path.getmtime(self._GetPath(strMine, strType))) > self.dctDirs[strMine]['status'][strType]['timestamp']:
                self.dctDirs[strMine]['status'][strType]['timestamp'] = timestamp
                lstModified.append(strType)
        return lstModified

    def GetNodes(self, strMine: str) -> dict:
        pthNodes = self._GetPath(strMine, 'nodes')
        self.node_data.SetPath(pthNodes)
        return self.node_data.GetData()
    
    def GetPlan(self, strMine: str, bounds: list[float]) -> dict:
        pthPlan = self._GetPath(strMine, 'plan')
        self.plan_pipeline.SetPaths(pthPlan)
        self.plan_pipeline.SetBounds(bounds)
        self.plan_pipeline.Update()
        return self.plan_pipeline.GetGeometry()
        
    def GetEvents(self, strMine: str, bounds: list[float], timestamp: float) -> dict:
        pthEvents = self._GetPath(strMine, 'events')
        self.event_data.SetPath(pthEvents)
        self.event_data.SetBounds(bounds)
        self.event_data.SetTimeStamp(timestamp)
        return self.event_data.GetData()
        
    def GetVolume(self, strMine: str) -> dict: #, bounds: list[float]) -> dict:
        pthVolume = self._GetPath(strMine, 'volume')
        self.volume_pipeline.SetPath(pthVolume)
        return self.volume_pipeline.GetImage()
                    

# Start Up Here ---------------------------------------------------------------

provider = DataProvider_FileSystem('C:\\Users\\Malcolm\\Projects\\Web\\TickerWeb\\Data')
provider.AddMine('Bambanani', 'Bambanani')
provider.AddMine('Skorrosh', 'Skorrosh')

# Flask stuff -----------------------------------

from flask import Flask, render_template, request
from flask_cors import CORS

app = Flask(__name__, template_folder='templates')
# enable CORS (Cross-Origin Resource Sharing) - so Flask can exchange data across domains
CORS(app, resources={r'/*': {'origins': '*'}})

@app.route('/')
def root():
    return render_template("index.html")
    
@app.route('/mines') # for login
def mines():
    return provider.GetMines()
   
@app.route('/modified', methods = ['PUT'])
def modified():
    json_dict = request.get_json()
    mine = json_dict['mine']
    return provider.GetModified(mine)
    
@app.route('/nodes', methods = ['PUT'])
def nodes_data():
    json_dict = request.get_json()
    mine = json_dict['mine']
    return provider.GetNodes(mine)

@app.route('/plan_vtk', methods = ['PUT'])
def plan():
    json_dict = request.get_json()
    bounds = json_dict['bounds']
    mine = json_dict['mine']
    return provider.GetPlan(mine, bounds)
    
@app.route('/volume_vtk', methods = ['PUT'])
def volume():
    json_dict = request.get_json()
    mine = json_dict['mine']
    return provider.GetVolume(mine)
    
@app.route('/events', methods = ['PUT'])
def events_data():
    json_dict = request.get_json()
    mine = json_dict['mine']
    bounds = json_dict.get('bounds', None)
    timestamp = json_dict.get('timestamp', 0)
    return provider.GetEvents(mine, bounds, timestamp)


if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True)
    