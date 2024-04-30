# press alt + shift + m to run the code from python straight into maya
import maya.cmds as mc

from PySide2.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton

def CreateBox(name, size):
    pntPositions = ((-0.5,0.5,0.5), (0.5,0.5,0.5), (0.5,0.5,-0.5), (-0.5, 0.5, -0.5), (-0.5, 0.5, 0.5), (-0.5, -0.5, 0.5), (0.5, -0.5, 0.5), (0.5, 0.5, 0.5), (0.5, -0.5, 0.5), (0.5, -0.5, -0.5), (0.5, 0.5, -0.5), (0.5, -0.5, -0.5), (-0.5, -0.5, -0.5), (-0.5, 0.5, -0.5), (-0.5, -0.5, -0.5), (-0.5, -0.5, 0.5))
    mc.curve(n = name, d=1, p = pntPositions)
    mc.setAttr(name + ".scale", size, size, size, type = "float3")
    mc.makeIdentity(name, apply = True)   # this is freeze transformation

def CreatePlus(name, size):
    pntPositions = ((0.5,0,1),(0.5,0,0.5),(1,0,0.5),(1,0,-0.5),(0.5, 0,-0.5), (0.5, 0, -1),(-0.5, 0, -1),(-0.5,0,-0.5),(-1, 0, -0.5),(-1,0,0.5),(-0.5,0,0.5),(-0.5,0,1),(0.5,0,1)) 
    mc.curve(n = name, d=1, p = pntPositions)
    mc.setAttr(name + ".scale", size, size, size, type = "float3")
    mc.makeIdentity(name, apply = True) # This is freeze transformation

def SetChannelHidden(name, channel):
    mc.setAttr(name + "." + channel, k=False, channelBox = False)

def CreateCircleController(jnt, size):
    name = "ac_" + jnt
    mc.circle(n = name, nr=(1,0,0), r = size/2)
    ctrlGrpName = name + "_grp"
    mc.group(name, n = ctrlGrpName)
    mc.matchTransform(ctrlGrpName, jnt)
    mc.orientConstraint(name, jnt)

    return name, ctrlGrpName

def GetObjPos(obj):
    # q means we are querying
    # t means we are querying the translate
    # ws means we are querying in the world space 
    pos = mc.xform(obj, q=True, t=True, ws=True)
    return Vector(pos[0], pos[1], pos[2])

def SetObjPos(obj, pos):
    mc.setAttr(obj + ".translate", pos.x, pos.y, pos.z, type = "float3")

class Vector:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    # This enables Vector + Vector
    def __add__(self, other):
        return Vector(self.x + other.x, self.y + other.y, self.z + other.z)
    
    # This enables Vector - Vector
    def __sub__(self, other):
        return Vector(self.x - other.x, self.y - other.y, self.z - other.z)
    
    # we are defining Vector * Float
    def __mul__(self, scalar):
        return Vector(self.x * scalar, self.y * scalar, self.z * scalar)
    
    # We are defining Vector / Float
    def __truediv__(self, scalar):
        return Vector(self.x / scalar, self.y / scalar, self.z / scalar)

    def GetLength(self):
        return (self.x ** 2 + self.y ** 2 + self.z ** 2) ** 0.5
    
    def GetNormalized(self):
        return self/self.GetLength()
    
    def __str__(self):
        return f"<{self.x} {self.y} {self.z}>"
    
class CreateLimbController:
    def __init__(self):
        self.root = ""
        self.mid = ""
        self.end = ""

    def FindJntsBaszedOnRootSel(self):
        self.root = mc.ls(sl=True, type = "joint")[0]
        self.mid = mc.listRelatives(self.root, c=True, type="joint")[0]
        self.end = mc.listRelatives(self.mid, c=True, type = "joint")[0]

    def RigLimb(self):
        rootCtrl, rootCtrlGrp = CreateCircleController(self.root, 20)
        midCtrl, midCtrlGrp = CreateCircleController(self.mid, 20)
        endCtrl, endCtrlGrp = CreateCircleController(self.end, 20)

        mc.parent(midCtrlGrp, rootCtrl)
        mc.parent(endCtrlGrp, midCtrl)

        ikEndCtrl = "ac_ik_" + self.end
        CreateBox(ikEndCtrl, 10)
        ikEndCtrlGrp = ikEndCtrl + "_grp"
        mc.group(ikEndCtrl, n = ikEndCtrlGrp)
        mc.matchTransform(ikEndCtrlGrp, self.end)
        endJntOrientConstraint = mc.orientConstraint(ikEndCtrl, self.end)[0]

        ikHandleName = "ikHandle_" + self.end
        mc.ikHandle(n=ikHandleName, sj = self.root, ee=self.end, sol="ikRPsolver")

        poleVector = mc.getAttr(ikHandleName+".poleVector")[0]
        poleVector = Vector(poleVector[0], poleVector[1], poleVector[2])
        poleVector = poleVector.GetNormalized()
    
        rootPos = GetObjPos(self.root)
        endPos = GetObjPos(self.end)

        print(rootPos)
        print(endPos)

        rootToEndVec = endPos - rootPos
        armHalfLength = rootToEndVec.GetLength()/2

        poleVecPos = rootPos + rootToEndVec/2 + poleVector * armHalfLength
        ikMidCtrl = "ac_ik_" + self.mid
        mc.spaceLocator(n=ikMidCtrl) # Make a locator with the name ac_ik_ + self.mid
        ikMidCtrlGrp = ikMidCtrl + "_grp" # figure out the group name of that locator
        mc.group(ikMidCtrl, n = ikMidCtrlGrp) # group the locator with the name
        SetObjPos(ikMidCtrlGrp, poleVecPos) # Make hte locator to the polvector location we fugured out
        mc.poleVectorConstraint(ikMidCtrl, ikHandleName) # Do pole vector constraint 
        mc.parent(ikHandleName, ikEndCtrl)
        mc.hide(ikHandleName)

        ikfkBlendCtrl = "ac_" + self.root + "_ikfkBlend"
        CreatePlus(ikfkBlendCtrl, 2)
        ikfkBlendCtrlGrp = ikfkBlendCtrl + "_grp"
        mc.group(ikfkBlendCtrl, n = ikfkBlendCtrlGrp)
        ikfkBlendControlPos = rootPos + Vector(rootPos.x,0,0)
        SetObjPos(ikfkBlendCtrlGrp, ikfkBlendControlPos)
        mc.setAttr(ikfkBlendCtrlGrp +".rx", 90)

        SetChannelHidden(ikfkBlendCtrl, 'tx')
        SetChannelHidden(ikfkBlendCtrl, 'ty')
        SetChannelHidden(ikfkBlendCtrl, 'tz')
        SetChannelHidden(ikfkBlendCtrl, 'rx')
        SetChannelHidden(ikfkBlendCtrl, 'ry')
        SetChannelHidden(ikfkBlendCtrl, 'rz')
        SetChannelHidden(ikfkBlendCtrl, 'sx')
        SetChannelHidden(ikfkBlendCtrl, 'sy')
        SetChannelHidden(ikfkBlendCtrl, 'sz')
        SetChannelHidden(ikfkBlendCtrl, 'v')

        ikfkBlendAttr = "ikfkBlend"
        mc.addAttr(ikfkBlendCtrl, ln=ikfkBlendAttr, k=True, min = 0, max = 1)
        mc.connectAttr(ikfkBlendCtrl + "." + ikfkBlendAttr, ikHandleName + ".ikBlend")

        reverseNode = "reverse_" + self.root + "_ikfkBlend"
        mc.createNode("reverse", n = reverseNode)

        mc.connectAttr(ikfkBlendCtrl + "." + ikfkBlendAttr, reverseNode+".inputX")
        mc.connectAttr(reverseNode + ".outputX", endJntOrientConstraint + ".w0")
        mc.connectAttr(ikfkBlendCtrl + "." + ikfkBlendAttr, endJntOrientConstraint+".w1")

        # IKFK Visibility Controls
        mc.connectAttr(ikfkBlendCtrl + "." + ikfkBlendAttr, ikMidCtrlGrp + ".v") 
        mc.connectAttr(reverseNode + ".outputX", rootCtrl + ".v") 
        mc.connectAttr(ikfkBlendCtrl + "." + ikfkBlendAttr, ikEndCtrlGrp + ".v") 
        mc.group(ikfkBlendCtrlGrp, ikEndCtrlGrp, ikMidCtrlGrp, rootCtrlGrp, n = rootCtrlGrp + "_limb") 

class CreateLimbControllerWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Create IKFK Limb")
        self.setGeometry(100,100,300,300)
        self.masterLayout = QVBoxLayout()
        self.setLayout(self.masterLayout)

        hintLabel = QLabel("Please Select the root of the Limb")
        self.masterLayout.addWidget(hintLabel)

        findJntsBtn = QPushButton("Find Jnts")
        findJntsBtn.clicked.connect(self.FindJntBtnClicked)

        self.masterLayout.addWidget(findJntsBtn)

        self.autoFindJntDisplay = QLabel("")
        self.masterLayout.addWidget(self.autoFindJntDisplay)
        self.adjustSize()

        rigLimbBtn = QPushButton("Rig Limb")
        rigLimbBtn.clicked.connect(self.RigLimbBtnClicked)
        self.masterLayout.addWidget(rigLimbBtn)

        self.createLimbCtrl = CreateLimbController()

    def FindJntBtnClicked(self):
        self.createLimbCtrl.FindJntsBaszedOnRootSel()
        self.autoFindJntDisplay.setText(f"{self.createLimbCtrl.root},{self.createLimbCtrl.mid},{self.createLimbCtrl.end}")

    def RigLimbBtnClicked(self):
        self.createLimbCtrl.RigLimb()

controllerWidget = CreateLimbControllerWidget()
controllerWidget.show()

