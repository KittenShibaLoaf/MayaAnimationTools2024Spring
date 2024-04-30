import os
from PySide2.QtCore import Signal
from PySide2.QtGui import QIntValidator, QRegExpValidator
import maya.cmds as mc
from PySide2.QtWidgets import QAbstractItemView, QCheckBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget, QMessageBox, QPushButton, QVBoxLayout, QWidget

class AnimClip:
    def __init__(self):
        self.frameStart = int(mc.playbackOptions(q = True, min = True))
        self.frameEnd = int(mc.playbackOptions(q = True, max = True))
        self.subfix = ""
        self.shouldExport = True

class MayaToUE:
    def __init__(self):
        self.rootJnt = ""
        self.meshes = set()
        self.fileName = ""
        self.animations = []
        self.saveDir = ""

    def SaveFiles (self):
        childrenJnts = mc.listRelatives(self.rootJnt, c = True, ad = True, type = "joint")
        allJnts = [self.rootJnt] + childrenJnts
        objsToExport = allJnts + list(self.meshes)

        mc.select(objsToExport, r = True)
        skeletalMeshSavePath = self.GetSkeletalMeshSavePath()

        mc.FBXResetExport()
        mc.FBXExportSmoothingGroups('-v', True)
        mc.FBXExportInputConnections('-v', False)
        
        mc.FBXExport('-f', skeletalMeshSavePath, '-s', True, '-ea', False)

        if not self.animations:
            return
        
        os.makedirs(self.GetAnimFolder(), exist_ok = True)
        mc.FBXExportBakeComplexAnimation('-v', True)
        for anim in self.animations:
            animSavePath = self.GetAnimClipSavePath(anim)
            
            startFrame = anim.frameStart
            endFrame = anim.frameEnd

            mc.FBXExportBakeComplexStart('-v', startFrame)
            mc.FBXExportBakeComplexEnd('-v', endFrame)
            mc.FBXExportBakeComplexStep('-v', 1)

            mc.playbackOptions(e = True, min = startFrame, max = endFrame)
            mc.FBXExport('-f', animSavePath, '-s', True, '-ea', True)


    def SetSaveDir(self, newSaveDir):
        self.saveDir = newSaveDir

    def GetSkeletalMeshSavePath(self):
        # In windows, this path could be: c:\\dev\myPrj\alex.fbx
        # In mac/linux, this path could be: ~/dev/myPrj/alex.fbx
        # Path could be c:\dev/myPrj\sdfsdf.fbx
        path = os.path.join(self.saveDir, self.fileName + ".fbx")
        return os.path.normpath(path) # Will convert the path based on the user you are on
    
    def GetAnimFolder(self):
        path = os.path.join(self.saveDir, "anim")
        return os.path.normpath(path)
    
    def GetAnimClipSavePath(self, clip: AnimClip):
        path = os.path.join(self.GetAnimFolder(), self.fileName + "_" + clip.subfix + ".fbx")
        return os.path.normpath(path)

    def AddAnimClip(self):
        self.animations.append(AnimClip())
        return self.animations[-1]

    def SetSelectedAsRootJnt(self):
        selection = mc.ls(sl = True, type = "joint")
        if not selection:
            return False, "No Joint Selected"
        
        self.rootJnt = selection[0]
        return True, ""
    
    def TryAddUnrealRootJnt(self):
        if (not self.rootJnt) or (not mc.objExists(self.rootJnt)):
            return False, "Need to Assign Root Joint First"
        
        # q means query, t means translate, ws means world space
        currentRootPos = mc.xform(self.rootJnt, q = True, t = True, ws = True)
        if currentRootPos[0] == 0 and currentRootPos[1] == 0 and currentRootPos[2] == 0:
            return False, "Root Joint Already Exists"
        
        rootJntName = self.rootJnt + "_root"
        mc.select(cl = True) # cl means cancel
        mc.joint(name = rootJntName)
        mc.parent(self.rootJnt, rootJntName)
        self.rootJnt = rootJntName
        return True, ""

    def SetSelectedAsMeshes(self):
        selection = mc.ls(sl = True)
        if not selection:
            return False, "No Mesh Selected"
        
        meshes = set()
        for sel in selection: # Loop through everything we select
            shapes = mc.listRelatives(sel, s = True) # Find thier shape nodes
            if not shapes:
                continue
            for s in shapes: # For each shape node we find
                if mc.objectType(s) == "mesh": # Check if there are mesh shapes
                    meshes.add(sel) # If they are mesh shapes, we will collect them

        if len(meshes) == 0:
            return False, "No Mesh Selected"
        
        self.meshes = meshes
        return True, ""
    
class AnimEntry(QWidget):
    entryNameChanged = Signal(str)
    entryRemoved = Signal(AnimClip)
    def __init__(self, animClip: AnimClip):
        super().__init__()
        self.animClip = animClip
        self.masterLayout = QHBoxLayout()
        self.setLayout(self.masterLayout)

        self.toggleBox = QCheckBox()
        self.toggleBox.setChecked(animClip.shouldExport)
        self.toggleBox.toggled.connect(self.ToggleBoxToggled)
        self.masterLayout.addWidget(self.toggleBox)

        subfixLabel = QLabel("Subfix: ")
        self.masterLayout.addWidget(subfixLabel)
        self.subfixLineEdit = QLineEdit()
        self.subfixLineEdit.setValidator(QRegExpValidator('\w+'))
        self.subfixLineEdit.textChanged.connect(self.SubfixTextChanged)
        self.subfixLineEdit.setText(animClip.subfix)
        self.masterLayout.addWidget(self.subfixLineEdit)

        startFrameLabel = QLabel("Start: ")
        self.masterLayout.addWidget(startFrameLabel)
        self.startFrameLineEdit = QLineEdit()
        self.startFrameLineEdit.setValidator(QIntValidator())
        self.startFrameLineEdit.textChanged.connect(self.StartFrameTextChanged)
        self.startFrameLineEdit.setText(str(animClip.frameStart))
        self.masterLayout.addWidget(self.startFrameLineEdit)

        endFrameLabel = QLabel("End: ")
        self.masterLayout.addWidget(endFrameLabel)
        self.endFrameLineEdit = QLineEdit()
        self.endFrameLineEdit.setValidator(QIntValidator())
        self.endFrameLineEdit.textChanged.connect(self.EndFrameTextChanged)
        self.endFrameLineEdit.setText(str(animClip.frameEnd))
        self.masterLayout.addWidget(self.endFrameLineEdit)

        setRangeBtn = QPushButton("[ - ]")
        setRangeBtn.clicked.connect(self.SetRangeBtnClicked)
        self.masterLayout.addWidget(setRangeBtn)
        
        removeBtn = QPushButton("[ X ]")
        removeBtn.clicked.connect(self.RemoveBtnClicked)
        self.masterLayout.addWidget(removeBtn)

    def SubfixTextChanged(self):
        if self.subfixLineEdit.text():
            self.animClip.subfix = self.subfixLineEdit.text()
            self.entryNameChanged.emit(self.animClip.subfix)

    def StartFrameTextChanged(self):
        if self.startFrameLineEdit.text():
            self.animClip.frameEnd = int(self.startFrameLineEdit.text())

    def EndFrameTextChanged(self):
        if self.endFrameLineEdit.text():
            self.animClip.frameStart = int(self.endFrameLineEdit.text())

    def ToggleBoxToggled(self):
        self.animClip.shouldExport = not self.animClip.shouldExport

    def SetRangeBtnClicked(self):
        mc.playbackOptions(minTime = self.animClip.frameStart, maxTime = self.animClip.frameEnd, e = True)

    def RemoveBtnClicked(self):
        self.entryRemoved.emit(self.animClip) # This calls the function connected to the entryRemoved Signal
        self.deleteLater() # Remove this widget the next time it is proper 

class MayaToUEWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.mayaToUE = MayaToUE()
        self.masterLayout = QVBoxLayout()
        self.setLayout(self.masterLayout)
        self.setFixedWidth(500)
        self.jntLineEdit = QLineEdit()
        self.jntLineEdit.setEnabled(False) # Makes it grayed out
        self.masterLayout.addWidget(self.jntLineEdit)

        setSelectedAsRootJntBtn = QPushButton("Set Selected As Root Joint")
        setSelectedAsRootJntBtn.clicked.connect(self.SetSelectedAsRootBtnClicked)
        self.masterLayout.addWidget(setSelectedAsRootJntBtn)

        addUnrealRootBtn = QPushButton("Add Unreal Root Joint")
        addUnrealRootBtn.clicked.connect(self.AddUnrealRootBtnClicked)
        self.masterLayout.addWidget(addUnrealRootBtn)

        self.meshList = QListWidget()
        self.meshList.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.meshList.setFixedHeight(80)
        self.meshList.itemSelectionChanged.connect(self.MeshListSelectionChanged)
        self.masterLayout.addWidget(self.meshList)

        assignSelectedMeshBtn = QPushButton("Assign Selected Meshes")
        assignSelectedMeshBtn.clicked.connect(self.AssignSelectedMeshBtnClicked)
        self.masterLayout.addWidget(assignSelectedMeshBtn)

        addAnimEntryBtn = QPushButton("Add New Animation Clip")
        addAnimEntryBtn.clicked.connect(self.AddNewAnimEntryBtnClicked)
        self.masterLayout.addWidget(addAnimEntryBtn)

        self.animEntryLayout = QVBoxLayout()
        self.masterLayout.addLayout(self.animEntryLayout)

        self.saveFileLayout = QHBoxLayout()
        self.masterLayout.addLayout(self.saveFileLayout)
        fileNameLabel = QLabel("Name: ")
        self.saveFileLayout.addWidget(fileNameLabel)
        self.fileNameLineEdit = QLineEdit()
        self.fileNameLineEdit.setFixedWidth(80)
        self.fileNameLineEdit.setValidator(QRegExpValidator("\w+"))
        self.fileNameLineEdit.textChanged.connect(self.FileNameChanged)
        self.saveFileLayout.addWidget(self.fileNameLineEdit)

        fileDirLabel = QLabel("Save Directory: ")
        self.saveFileLayout.addWidget(fileDirLabel)
        self.saveDirLineEdit = QLineEdit()
        self.saveDirLineEdit.setEnabled(False)
        self.saveFileLayout.addWidget(self.saveDirLineEdit)

        setSaveDirBtn = QPushButton("...")
        setSaveDirBtn.clicked.connect(self.SetSaveDirBtnClicked)
        self.saveFileLayout.addWidget(setSaveDirBtn)

        self.savePreviewLabel = QLabel()
        self.masterLayout.addWidget(self.savePreviewLabel)

        saveBtn = QPushButton("Save Files")
        saveBtn.clicked.connect(self.mayaToUE.SaveFiles)
        self.masterLayout.addWidget(saveBtn)


    def UpdateSavePreview(self):
        previewText = ""
        skeletalMeshFilePath = self.mayaToUE.GetSkeletalMeshSavePath()
        previewText += skeletalMeshFilePath

        if self.mayaToUE.animations:
            for anim in self.mayaToUE.animations:
                animPath = self.mayaToUE.GetAnimClipSavePath(anim)
                previewText += "\n" + animPath

        self.savePreviewLabel.setText(previewText)
        self.adjustSize()

    def SetSaveDirBtnClicked(self):
        # This selects folders through Maya 
            # path = mc.fileDialog2(dir = "~/", dialogStyle = 2, fileMode = 3)

        # This selects folders through Windows. This is a better option as it doesn't rely on Maya
        dir = QFileDialog().getExistingDirectory()
        self.mayaToUE.saveDir = dir
        self.saveDirLineEdit.setText(dir)
        self.UpdateSavePreview()

    def FileNameChanged(self, newName):
        self.mayaToUE.fileName = newName
        self.UpdateSavePreview()

    def AddNewAnimEntryBtnClicked(self):
        newClip = self.mayaToUE.AddAnimClip()
        newEntry = AnimEntry(newClip)
        newEntry.entryRemoved.connect(self.RemoveAnimEntry)
        newEntry.entryNameChanged.connect(self.UpdateSavePreview)
        self.animEntryLayout.addWidget(newEntry)
        self.UpdateSavePreview()

    def RemoveAnimEntry(self, clipToRemove):
        self.adjustSize()
        self.mayaToUE.animations.remove(clipToRemove)
        self.UpdateSavePreview()

    def AssignSelectedMeshBtnClicked(self):
        success, msg = self.mayaToUE.SetSelectedAsMeshes()
        if success:
            self.meshList.clear()
            self.meshList.addItems(self.mayaToUE.meshes)
        else:
            QMessageBox().warning(self, "Warning", msg)

    def MeshListSelectionChanged(self):
        mc.select(cl = True)
        for item in self.meshList.selectedItems():
            mc.select(item.text(), add = True)

    def AddUnrealRootBtnClicked(self):
        success, msg = self.mayaToUE.TryAddUnrealRootJnt
        if success:
            self.jntLineEdit.setText(self.mayaToUE.rootJnt)
        else:
            QMessageBox().warning(self, "Warning", msg)

    def SetSelectedAsRootBtnClicked(self):
        success, msg = self.mayaToUE.SetSelectedAsRootJnt()
        if success:
            self.jntLineEdit.setText(self.mayaToUE.rootJnt)
        else:
            QMessageBox().warning(self, "Warning", msg)


mayaToUEWidget = MayaToUEWidget()
mayaToUEWidget.show()