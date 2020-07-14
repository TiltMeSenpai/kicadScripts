#!/usr/bin/python3
'''
    A python script example to create various plot files from a board:
    Fab files
    Doc files
    Gerber files

    Important note:
        this python script does not plot frame references.
        the reason is it is not yet possible from a python script because plotting
        plot frame references needs loading the corresponding page layout file
        (.wks file) or the default template.

        This info (the page layout template) is not stored in the board, and therefore
        not available.

        Do not try to change SetPlotFrameRef(False) to SetPlotFrameRef(true)
        the result is the pcbnew lib will crash if you try to plot
        the unknown frame references template.
'''

import sys
import os
import pcbnew
import time
import re

import logging
import zipfile
import shutil


from pcbnew import *
from datetime import datetime
from shutil import copy



filename = os.environ.get("PCB_PATH",    sys.argv[1])
git_rev  = os.environ.get("PCB_VERSION", sys.argv[2])
project_name = os.path.splitext(os.path.split(filename)[1])[0]
project_path = os.path.abspath(os.path.split(filename)[0])

output_directory = os.path.join(project_path,'plot')

today = datetime.now().strftime('%Y%m%d_%H%M%S')

board = LoadBoard(filename)

pctl = PLOT_CONTROLLER(board)

popt = pctl.GetPlotOptions()

popt.SetOutputDirectory(output_directory)

# Set some important plot options:
popt.SetPlotFrameRef(False)
# Nightly doesn't like SetLineWidth
try:
    popt.SetLineWidth(FromMM(0.35))
except AttributeError:
    pass

popt.SetAutoScale(False)
popt.SetScale(1)
popt.SetMirror(False)
popt.SetUseGerberAttributes(False)
popt.SetExcludeEdgeLayer(True)
popt.SetScale(1)
popt.SetUseAuxOrigin(True)
popt.SetNegative(False)
popt.SetPlotReference(True)
popt.SetPlotValue(True)
popt.SetPlotInvisibleText(False)

# This by gerbers only (also the name is truly horrid!)
popt.SetSubtractMaskFromSilk(True) #remove solder mask from silk to be sure there is no silk on pads

for module in board.GetDrawings():
    if(isinstance(module, pcbnew.TEXTE_PCB)):
        if "${GIT_REV}" in module.GetText():
            module.SetText(module.GetText().replace("${GIT_REV}", git_rev))
            print(f"Git Revision Replaced: {git_rev}")

plot_plan = [
    ( "F_Cu", F_Cu, "Top layer"),
    ( "B_Cu", B_Cu, "Bottom layer"),
    ( "B_Mask", B_Mask, "Mask Bottom"),
    ( "F_Mask", F_Mask, "Mask top"),
    ( "B_Paste", B_Paste, "Paste Bottom"),
    ( "F_Paste", F_Paste, "Paste Top"),
    ( "F_SilkS", F_SilkS, "Silk Top"),
    ( "B_SilkS", B_SilkS, "Silk Bottom"),
    ( "Edge_Cuts", Edge_Cuts, "Edges")
]

popt.SetMirror(False)
popt.SetDrillMarksType(PCB_PLOT_PARAMS.NO_DRILL_SHAPE)
print("Plotting Gerber Layers:")

fab_files = []

# Functional Gerber Plots 
for layer_info in plot_plan:
    pctl.SetLayer(layer_info[1])
    pctl.OpenPlotfile(layer_info[0], PLOT_FORMAT_GERBER, layer_info[2])
    pctl.PlotLayer()
    time.sleep(0.01)
    pctl.ClosePlot()
    plotFile = pctl.GetPlotFileName()
    print(f"Plotted {plotFile}")
    fab_files.append(plotFile)


#generate internal copper layers, if any
lyrcnt = board.GetCopperLayerCount();

for innerlyr in range ( 1, lyrcnt-1 ):
    pctl.SetLayer(innerlyr)
    lyrname = 'inner%s' % innerlyr
    pctl.OpenPlotfile(lyrname, PLOT_FORMAT_GERBER, "inner")
    pctl.PlotLayer()
    time.sleep(0.01)
    pctl.ClosePlot()
    plotFile = pctl.GetPlotFileName()
    print(f"Plotted {plotFile}")
    fab_files.append(plotFile)

# Fabricators need drill files.
# sometimes a drill map file is asked (for verification purpose)
drlwriter = EXCELLON_WRITER( board )
drlwriter.SetMapFileFormat( PLOT_FORMAT_PDF )

mirror = False
minimalHeader = False

if popt.GetUseAuxOrigin():
    def aux_origin_missing():
        popt.SetUseAuxOrigin(False)
        return wxPoint(0, 0)
    offset = getattr(board, "GetAuxOrigin", aux_origin_missing)()
else:
    offset = wxPoint(0,0)

mergeNPTH = False
drlwriter.SetOptions( mirror, minimalHeader, offset, mergeNPTH )

metricFmt = True
drlwriter.SetFormat( metricFmt )

genDrl = True
genMap = True
drlwriter.CreateDrillandMapFilesSet( output_directory, genDrl, genMap )

drlPlot = os.path.join(output_directory,project_name + '-PTH.drl')
print("Plotted" + drlPlot)
fab_files.append(drlPlot)
drlPlot = os.path.join(output_directory,project_name + '-NPTH.drl')
print("Plotted" + drlPlot)
fab_files.append(drlPlot)

# One can create a text file to report drill statistics
rptfn = output_directory + '/drill_report.txt'
drlwriter.GenDrillReportFile( rptfn )

# We have just generated your plotfiles with a single script
