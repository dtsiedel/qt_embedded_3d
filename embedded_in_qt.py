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

import argparse
import numpy as np
import math
import functools
from matplotlib.colors import Normalize
from matplotlib.cm import get_cmap

from mayavi.scripts import mayavi2
from tvtk.tools import mlab
from mayavi.sources.vtk_data_source import VTKDataSource
from mayavi.filters.warp_scalar import WarpScalar
from mayavi.modules.outline import Outline
from mayavi.modules.surface import Surface


class Visualization(HasTraits):
    # Not sure what this class has going on that messes with its constructor,
    # but I couldn't figure out how to override it so I just sideload all the
    # args in.
    scene = Instance(MlabSceneModel, ())

    def set_image(self, image, circle):
        # All images must be square, because I said so
        self.side_length = image.shape[0]

        if circle is not None:
            center = self.side_length / 2
            for x in range(self.side_length):
                for y in range(self.side_length):
                    x_diff = x - center
                    y_diff = y - center
                    distance = math.sqrt(x_diff**2 + y_diff**2)

                    if distance > circle:
                        image[x, y] = np.nan
        self.image = image

    def get_mayavi(self):
        return self.scene.engine

    def numpy_data(self):
        return self.image

    def vtk_data(self, array):
        """Convert ndarray to a Surface."""
        x = np.arange(0, array.shape[0], 1)
        y = np.arange(0, array.shape[1], 1)
        # scale z axis by side length
        s = mlab.SurfRegular(x, y, self.side_length * array)
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
        array = self.numpy_data()
        d = self.vtk_data(array)
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


class MayaviQWidget(QtGui.QWidget):
    def __init__(self, image, circle, parent=None):
        QtGui.QWidget.__init__(self, parent)
        layout = QtGui.QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)
        self.visualization = Visualization()
        self.visualization.set_image(image, circle)

        # The edit_traits call will generate the widget to embed.
        self.ui = self.visualization.edit_traits(parent=self,
                                                 kind='subpanel').control
        layout.addWidget(self.ui)
        self.ui.setParent(self)


class NotImageWidget(QtGui.QWidget):
    def __init__(self, data=None, parent=None):
        QtGui.QWidget.__init__(self, parent)

        cmap = get_cmap('jet')
        mapped = 255*np.array([cmap(x) for x in data])
        no_a = mapped[:,:,:-1]

        height, width, _ = no_a.shape
        bytes_per_line = 3 * width
        no_a = no_a.astype(np.uint8)
        image = QtGui.QImage(no_a, width, height, bytes_per_line,
                             QtGui.QImage.Format_RGB888)
        label = QtGui.QLabel()
        label.setPixmap(QtGui.QPixmap.fromImage(image))

        layout = QtGui.QHBoxLayout()
        layout.addWidget(label)
        self.setLayout(layout)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-file')
    parser.add_argument('-circle', nargs='?', type=int, default=None)
    args = parser.parse_args()
    # Don't create a new QApplication, it would unhook the Events
    # set by Traits on the existing QApplication. Simply use the
    # '.instance()' method to retrieve the existing one.
    app = QtGui.QApplication.instance()
    container = QtGui.QWidget()
    input_image = np.load(args.file)
    while len(input_image.shape) > 2:
        input_image = input_image[0]
    norm = Normalize(vmin=np.nanmin(input_image), vmax=np.nanmax(input_image))
    input_image = np.array([norm(x) for x in input_image])
    mayavi_widget = MayaviQWidget(input_image, args.circle, container)
    image = NotImageWidget(mayavi_widget.visualization.numpy_data())
    container.setWindowTitle("Embedding Mayavi in a PyQt Application")
    # define a "complex" layout to test the behaviour
    layout = QtGui.QHBoxLayout(container)

    layout.addWidget(image)
    layout.addWidget(mayavi_widget)
    container.show()
    window = QtGui.QMainWindow()
    window.setCentralWidget(container)
    window.show()

    # Start the main event loop.
    app.exec_()
