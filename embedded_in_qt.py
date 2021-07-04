
# First, and before importing any Enthought packages, set the ETS_TOOLKIT
# environment variable to qt4, to tell Traits that we will use Qt.
# This is true even when using qt5 (as we are)
import os
os.environ['ETS_TOOLKIT'] = 'qt4'
# By default, the PySide binding will be used. If you want the PyQt bindings
# to be used, you need to set the QT_API environment variable to 'pyqt'
os.environ['QT_API'] = 'pyqt5'

# To be able to use PySide or PyQt4 and not run in conflicts with traits,
# we need to import QtGui and QtCore from pyface.qt
from pyface.qt import QtGui, QtCore
# Alternatively, you can bypass this line, but you need to make sure that
# the following lines are executed before the import of PyQT:
#import sip
#sip.setapi('QString', 2)

from traits.api import HasTraits, Instance, on_trait_change
from traitsui.api import View, Item
from mayavi.core.ui.api import MayaviScene, MlabSceneModel, \
        SceneEditor

import numpy

from mayavi.scripts import mayavi2
from tvtk.tools import mlab
from mayavi.sources.vtk_data_source import VTKDataSource
from mayavi.filters.warp_scalar import WarpScalar
from mayavi.modules.outline import Outline
from mayavi.modules.surface import Surface


class Visualization(HasTraits):
    scene = Instance(MlabSceneModel, ())

    def get_mayavi(self):
        return self.scene.engine

    def make_data(self):
        """Make some test numpy test data and return it in a Surface."""
        def f(x, y):
            """Some test function."""
            return numpy.sin(x*y)/(x*y)

        x = numpy.arange(-7., 7.05, 0.1)
        y = numpy.arange(-5., 5.05, 0.05)
        s = mlab.SurfRegular(x, y, f)
        return s.data

    def add_data(self, data):
        """Set tvk Dataset as data"""
        mv = self.get_mayavi()
        d = VTKDataSource()
        d.data = data
        mv.add_source(d)

    def surf_regular(self):
        """Now visualize the data as done in mlab."""
        mv = self.get_mayavi()
        w = WarpScalar()
        mv.add_filter(w)
        o = Outline()
        s = Surface()
        mv.add_module(o)
        mv.add_module(s)

    def render(self):
        mv = self.get_mayavi()
        d = self.make_data()
        self.add_data(d)
        self.surf_regular()

    @on_trait_change('scene.activated')
    def update_plot(self):
        # This function is called when the view is opened. We don't
        # populate the scene when the view is not yet open, as some
        # VTK features require a GLContext.

        self.render() 

    # the layout of the dialog screated
    view = View(Item('scene', editor=SceneEditor(scene_class=MayaviScene),
                     height=250, width=300, show_label=False), resizable=True)


################################################################################
# The QWidget containing the visualization, this is pure PyQt4 code.
class MayaviQWidget(QtGui.QWidget):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        layout = QtGui.QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)
        self.visualization = Visualization()

        # The edit_traits call will generate the widget to embed.
        self.ui = self.visualization.edit_traits(parent=self,
                                                 kind='subpanel').control
        layout.addWidget(self.ui)
        self.ui.setParent(self)


if __name__ == "__main__":
    # Don't create a new QApplication, it would unhook the Events
    # set by Traits on the existing QApplication. Simply use the
    # '.instance()' method to retrieve the existing one.
    app = QtGui.QApplication.instance()
    container = QtGui.QWidget()
    mayavi_widget = MayaviQWidget(container)
    container.setWindowTitle("Embedding Mayavi in a PyQt Application")
    # define a "complex" layout to test the behaviour
    layout = QtGui.QHBoxLayout(container)

    layout.addWidget(QtGui.QLabel('2D image goes here'))
    layout.addWidget(mayavi_widget)
    container.show()
    window = QtGui.QMainWindow()
    window.setCentralWidget(container)
    window.show()

    # Start the main event loop.
    app.exec_()
