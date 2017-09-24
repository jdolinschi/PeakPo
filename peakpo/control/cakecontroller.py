import os
from PyQt5 import QtWidgets
import numpy as np
from utils import dialog_savefile, writechi
from .mplcontroller import MplController
from .cakemakecontroller import CakemakeController


class CakeController(object):

    def __init__(self, model, widget):
        self.model = model
        self.widget = widget
        self.cakemake_ctrl = CakemakeController(self.model, self.widget)
        self.plot_ctrl = MplController(self.model, self.widget)
        self.connect_channel()

    def connect_channel(self):
        self.widget.checkBox_ShowCake.clicked.connect(
            self.addremove_cake)
        self.widget.pushButton_GetPONI.clicked.connect(self.get_poni)
        self.widget.pushButton_ApplyCakeView.clicked.connect(
            self._apply_changes_to_graph)
        self.widget.pushButton_ApplyMask.clicked.connect(self.apply_mask)
        self.widget.pushButton_IntegrateCake.clicked.connect(
            self.integrate_to_1d)
        self.widget.checkBox_WhiteForPeak.clicked.connect(
            self._apply_changes_to_graph)
        self.widget.pushButton_AddAzi.clicked.connect(
            self._add_azi_to_list)
        self.widget.pushButton_RemoveAzi.clicked.connect(
            self._remove_azi_from_list)
        self.widget.pushButton_ClearAziList.clicked.connect(
            self._clear_azilist)

    def _add_azi_to_list(self):
        # read azimuth_range
        azi_range = self._read_azi_from_plot()
        if azi_range is None:
            return
        rowPosition = self.widget.tableWidget_DiffImgAzi.rowCount()
        self.widget.tableWidget_DiffImgAzi.insertRow(rowPosition)
        self.widget.tableWidget_DiffImgAzi.setItem(
            rowPosition, 0, QtWidgets.QTableWidgetItem(str(azi_range[0])))
        self.widget.tableWidget_DiffImgAzi.setItem(
            rowPosition, 1, QtWidgets.QTableWidgetItem(str(azi_range[1])))
        self._apply_changes_to_graph()

    def _remove_azi_from_list(self):
        # get higtlighted row, if not return
        rows = self.widget.tableWidget_DiffImgAzi.selectionModel().\
            selectedRows()
        if rows == []:
            QtWidgets.QMessageBox.warning(
                self.widget, 'Warning', 'Highlight the row to remove first.')
            return
        # update plot to highligh the selected row
        self._apply_changes_to_graph()
        reply = QtWidgets.QMessageBox.question(
            self.widget, 'Message',
            'The red highlighted area will be removed from the list, OK?',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.Yes)
        if reply == QtWidgets.QMessageBox.No:
            return
        # remove the row
        for r in rows:
            self.widget.tableWidget_DiffImgAzi.removeRow(r.row())
        self._apply_changes_to_graph()

    def _read_azilist(self):
        n_row = self.widget.tableWidget_DiffImgAzi.rowCount()
        if n_row == 0:
            return None
        azi_list = []
        for i in range(n_row):
            azi_min = float(
                self.widget.tableWidget_DiffImgAzi.item(i, 0).text())
            azi_max = float(
                self.widget.tableWidget_DiffImgAzi.item(i, 1).text())
            azi_list.append([azi_min, azi_max])
        return azi_list

    def _clear_azilist(self):
        self.widget.tableWidget_DiffImgAzi.setRowCount(0)
        self._apply_changes_to_graph()

    def _read_azi_from_plot(self):
        tth_range, azi_range = self.plot_ctrl.get_cake_range()
        if tth_range is None:
            return None
        else:
            return azi_range

    def integrate_to_1d(self):
        azi_range = self._read_azilist()
        if azi_range is None:
            QtWidgets.QMessageBox.warning(
                self.widget, 'Warning', 'No azimuthal ranges in the queue.')
            return
        # self.produce_cake()
        self.cakemake_ctrl.read_settings()
        tth = []
        intensity = []
        for azi_i in azi_range:
            tth_i, intensity_i = self.model.diff_img.integrate_to_1d(
                azimuth_range=azi_i)
            tth.append(tth_i)
            intensity.append(intensity_i)
        intensity_merged = np.zeros_like(intensity[0])
        for tth_i, intensity_i in zip(tth, intensity):
            if not np.array_equal(tth_i, tth[0]):
                QtWidgets.QMessageBox.warning(
                    self.widget, 'Warning', 'Error occured.  No output.')
                return
            intensity_merged += intensity_i
        n_azi = azi_range.__len__()
        first_azi = azi_range[0]
        ext = "{0:d}_{1:d}_{2:d}.chi".format(
            n_azi, int(first_azi[0]), int(first_azi[1]))
        filen_chi_t = self.model.make_filename(ext)
        filen_chi = dialog_savefile(self.widget, filen_chi_t)
        if str(filen_chi) == '':
            return
        azi_text = '# azimuthal angles: '
        for azi_i in azi_range:
            azi_text += "({0:.5e}, {1:.5e})".format(azi_i[0], azi_i[1])
        preheader_line0 = azi_text + ' \n'
        preheader_line1 = '\n'
        preheader_line2 = '\n'
        writechi(filen_chi, tth[0], intensity_merged, preheader=preheader_line0 +
                 preheader_line1 + preheader_line2)
    """
    def integrate_to_1d(self):
        azi_range = self._read_azi_from_plot()
        if azi_range is None:
            return
        # self.produce_cake()
        self.cakemake_ctrl.read_settings()
        tth, intensity = self.model.diff_img.integrate_to_1d(
            azimuth_range=azi_range)
        ext = "{0:d}to{1:d}.chi".format(int(azi_range[0]), int(azi_range[1]))
        filen_chi_t = self.model.make_filename(ext)
        filen_chi = dialog_savefile(self.widget, filen_chi_t)
        if str(filen_chi) == '':
            return
        preheader_line0 = \
            '# azimutal angle: {0: .5e}, {1: .5e} \n'.format(
                azi_range[0], azi_range[1])
        preheader_line1 = '\n'
        preheader_line2 = '\n'
        writechi(filen_chi, tth, intensity, preheader=preheader_line0 +
                 preheader_line1 + preheader_line2)
    """

    def _apply_changes_to_graph(self):
        self.plot_ctrl.update()

    def addremove_cake(self):
        """
        add / remove cake to the graph
        """
        update = self._addremove_cake()
        if update:
            self._apply_changes_to_graph()

    def _addremove_cake(self):
        """
        add / remove cake
        no signal to update_graph
        """
        if not self.widget.checkBox_ShowCake.isChecked():
            return True
        if not self.model.poni_exist():
            QtWidgets.QMessageBox.warning(
                self.widget, 'Warning', 'Choose PONI file first.')
            self.widget.checkBox_ShowCake.setChecked(False),
            return False
        if not self.model.base_ptn_exist():
            QtWidgets.QMessageBox.warning(
                self.widget, 'Warning', 'Choose CHI file first.')
            self.widget.checkBox_ShowCake.setChecked(False)
            return False
        filen_tif = self.model.make_filename('tif', original=True)
        filen_mar3450 = self.model.make_filename('mar3450', original=True)
        if not (os.path.exists(filen_tif) or os.path.exists(filen_mar3450)):
            QtWidgets.QMessageBox.warning(
                self.widget, 'Warning', 'Cannot find %s or %s.' %
                filen_tif, filen_mar3450)
            self.widget.checkBox_ShowCake.setChecked(False)
            return False
        if self.model.diff_img_exist() and \
                self.model.same_filename_as_base_ptn(
                self.model.diff_img.img_filename):
            return True
        self.process_temp_cake()
        return True

    def _load_new_image(self):
        """
        Load new image for cake view.  Cake should be the same as base pattern.
        no signal to update_graph
        """
        self.model.reset_diff_img()
        self.model.load_associated_img()
        self.widget.textEdit_DiffractionImageFilename.setText(
            self.model.diff_img.img_filename)

    def apply_mask(self):
        self.produce_cake()
        self._apply_changes_to_graph()

    def produce_cake(self):
        """
        Reprocess to get cake.  Slower re - processing
        does not signal to update_graph
        """
        self._load_new_image()
        self.cakemake_ctrl.cook()

    def process_temp_cake(self):
        """
        load cake through either temporary file or make a new cake
        """
        if not self.model.associated_image_exists():
            QtWidgets.QMessageBox.warning(
                self.widget, "Warning",
                "Image file for the base pattern does not exist.")
            return
        temp_dir = os.path.join(self.model.chi_path, 'temporary_pkpo')
        if self.widget.checkBox_UseTempCake.isChecked():
            if os.path.exists(temp_dir):
                self._load_new_image()
                success = self.model.diff_img.read_cake_from_tempfile(
                    temp_dir=temp_dir)
                if success:
                    pass
                else:
                    self._update_temp_cake_files(temp_dir)
            else:
                os.makedirs(temp_dir)
                self._update_temp_cake_files(temp_dir)
        else:
            self._update_temp_cake_files(temp_dir)

    def _update_temp_cake_files(self, temp_dir):
        self.produce_cake()
        self.model.diff_img.write_temp_cakefiles(temp_dir=temp_dir)

    def get_poni(self):
        """
        Opens a pyFAI calibration file
        signal to update_graph
        """
        filen = QtWidgets.QFileDialog.getOpenFileName(
            self.widget, "Open a PONI File",
            self.model.chi_path, "PONI files (*.poni)")[0]
        filename = str(filen)
        if os.path.exists(filename):
            self.model.poni = filename
            self.widget.textEdit_PONI.setText(self.model.poni)
            if self.model.diff_img_exist():
                self.produce_cake()
            self._apply_changes_to_graph()
