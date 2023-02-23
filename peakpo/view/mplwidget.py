import os
import sys
import numpy as np
from PyQt5 import QtCore, QtGui
from PyQt5 import QtWidgets
import ctypes
from matplotlib.backends.qt_compat import QT_API, _enum
from matplotlib.backends.backend_qt import FigureCanvasQT, NavigationToolbar2QT as NavigationToolbar
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec
import matplotlib.style as mplstyle
from matplotlib.transforms import Bbox
from matplotlib import cbook

DEBUG = False


class FigureCanvasQT_modified(FigureCanvasQT):
    def drawRectangle(self, rect):
        # Draw the zoom rectangle to the QPainter.  _draw_rect_callback needs
        # to be called at the end of paintEvent.
        if rect is not None:
            x0, y0, w, h = [int(pt / self.device_pixel_ratio) for pt in rect]
            x1 = x0 + w
            y1 = y0 + h
            def _draw_rect_callback(painter):
                pen = QtGui.QPen(
                    QtGui.QColor("red"),
                    3 / self.device_pixel_ratio
                )

                pen.setDashPattern([3, 3])
                for color, offset in [
                        (QtGui.QColor("red"), 0),
                        (QtGui.QColor(0,0,0,0), 3),
                ]:
                    pen.setDashOffset(offset)
                    pen.setColor(color)
                    painter.setPen(pen)
                    # Draw the lines from x0, y0 towards x1, y1 so that the
                    # dashes don't "jump" when moving the zoom box.
                    painter.drawLine(x0, y0, x0, y1)
                    painter.drawLine(x0, y0, x1, y0)
                    painter.drawLine(x0, y1, x1, y1)
                    painter.drawLine(x1, y0, x1, y1)
        else:
            def _draw_rect_callback(painter):
                return
        self._draw_rect_callback = _draw_rect_callback
        self.update()


class FigureCanvasQTAgg_modified(FigureCanvasAgg, FigureCanvasQT_modified):

    def paintEvent(self, event):
        """
        Copy the image from the Agg canvas to the qt.drawable.
        In Qt, all drawing should be done inside of here when a widget is
        shown onscreen.
        """
        self._draw_idle()  # Only does something if a draw is pending.

        # If the canvas does not have a renderer, then give up and wait for
        # FigureCanvasAgg.draw(self) to be called.
        if not hasattr(self, 'renderer'):
            return

        painter = QtGui.QPainter(self)
        try:
            # See documentation of QRect: bottom() and right() are off
            # by 1, so use left() + width() and top() + height().
            rect = event.rect()
            # scale rect dimensions using the screen dpi ratio to get
            # correct values for the Figure coordinates (rather than
            # QT5's coords)
            width = rect.width() * self.device_pixel_ratio
            height = rect.height() * self.device_pixel_ratio
            left, top = self.mouseEventCoords(rect.topLeft())
            # shift the "top" by the height of the image to get the
            # correct corner for our coordinate system
            bottom = top - height
            # same with the right side of the image
            right = left + width
            # create a buffer using the image bounding box
            bbox = Bbox([[left, bottom], [right, top]])
            buf = memoryview(self.copy_from_bbox(bbox))

            if QT_API == "PyQt6":
                from PyQt6 import sip
                ptr = int(sip.voidptr(buf))
            else:
                ptr = buf

            painter.eraseRect(rect)  # clear the widget canvas
            qimage = QtGui.QImage(ptr, buf.shape[1], buf.shape[0],
                                  _enum("QtGui.QImage.Format").Format_RGBA8888)
            qimage.setDevicePixelRatio(self.device_pixel_ratio)
            # set origin using original QT coordinates
            origin = QtCore.QPoint(rect.left(), rect.top())
            painter.drawImage(origin, qimage)
            # Adjust the buf reference count to work around a memory
            # leak bug in QImage under PySide.
            if QT_API == "PySide2" and QtCore.__version_info__ < (5, 12):
                ctypes.c_long.from_address(id(buf)).value = 1

            self._draw_rect_callback(painter)
        finally:
            painter.end()

    def print_figure(self, *args, **kwargs):
        super().print_figure(*args, **kwargs)
        self.draw()

class MplCanvas(FigureCanvasQTAgg_modified):
    """Class to represent the FigureCanvas widget"""

    def __init__(self):
        # setup Matplotlib Figure and Axis
        self.fig = Figure()
        bbox = self.fig.get_window_extent().transformed(
            self.fig.dpi_scale_trans.inverted())
        width, height = bbox.width * self.fig.dpi, bbox.height * self.fig.dpi
        self.fig.subplots_adjust(
            left = 50 / width, #40 / width,
            bottom = 30 / height, #20 / height
            right = 1 - 20 / width, # 1 - 5 / width,
            top = 1 - 30 / height,
            hspace = 0.0)
        # left=0.07, right=0.98,
        # top=0.94, bottom=0.07, hspace=0.0)
        self._define_axes(1)
        self.set_toNight(True)
        FigureCanvasQTAgg_modified.__init__(self, self.fig)
        FigureCanvasQTAgg_modified.setSizePolicy(
            self, QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding)
        FigureCanvasQTAgg_modified.updateGeometry(self)

    def _define_axes(self, h_cake):
        self.gs = GridSpec(100, 1)
        self.ax_pattern = self.fig.add_subplot(self.gs[h_cake + 1:99, 0])
        self.ax_cake = self.fig.add_subplot(self.gs[0:h_cake, 0],
                                            sharex=self.ax_pattern)
        self.ax_pattern.set_ylabel('Intensity (arbitrary unit)')
        self.ax_pattern.ticklabel_format(
            axis='y', style='sci', scilimits=(-2, 2))
        self.ax_pattern.get_yaxis().get_offset_text().set_position(
            (-0.04, -0.1))

    def resize_axes(self, h_cake):
        self.fig.clf()
        self._define_axes(h_cake)
        if h_cake == 1:
            self.ax_cake.tick_params(
                axis='y', colors=self.objColor, labelleft=False)
            self.ax_cake.spines['right'].set_visible(False)
            self.ax_cake.spines['left'].set_visible(False)
            self.ax_cake.spines['top'].set_visible(False)
            self.ax_cake.spines['bottom'].set_visible(False)
        elif h_cake >= 10:
            self.ax_cake.set_ylabel("Azimuth (degrees)")

    def set_toNight(self, NightView=True):
        if NightView:
            try:
                mplstyle.use(
                    os.path.join(os.path.curdir, 'mplstyle', 'night.mplstyle'))
            except:
                mplstyle.use('dark_background')
            self.bgColor = 'black'
            self.objColor = 'white'
        else:
            try:
                mplstyle.use(
                    os.path.join(os.path.curdir, 'mplstyle', 'day.mplstyle'))
            except:
                mplstyle.use('classic')
            self.bgColor = 'white'
            self.objColor = 'black'
#        self.fig.clf()
#        self.ax_pattern.cla()
#        Cursor(self.ax, useblit=True, color=self.objColor, linewidth=2 )
        self.fig.set_facecolor(self.bgColor)
        self.ax_cake.tick_params(which='both', axis='x',
                                 colors=self.objColor, direction='in',
                                 labelbottom=False, labeltop=False)
        #self.ax_cake.tick_params(axis='both', which='both', length=0)
        self.ax_cake.tick_params(axis='x', which='both', length=0)
        self.ax_pattern.xaxis.set_label_position('bottom')


class MplWidget(QtWidgets.QWidget):
    """Widget defined in Qt Designer"""

    def __init__(self, parent=None):
        # initialization of Qt MainWindow widget
        QtWidgets.QWidget.__init__(self, parent)
        # set the canvas to the Matplotlib widget
        self.canvas = MplCanvas()
        #
        self.canvas.setParent(self)
        self.canvas.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.canvas.setFocus()
        # create a vertical box layout
        self.vbl = QtWidgets.QVBoxLayout()
        # add navigation toolbar
        self.ntb = NavigationToolbar(self.canvas, self)
        # pack these widget into the vertical box
        self.vbl.addWidget(self.ntb)
        # add mpl widget to the vertical box
        self.vbl.addWidget(self.canvas)
        # set the layout to the vertical box
        self.setLayout(self.vbl)
