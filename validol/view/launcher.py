import sys
from PyQt5 import QtCore, QtWidgets, QtGui
import os
import re
import requests
from collections import defaultdict

from validol.view.graph.graphs import CheckedGraph
from validol.view.menu.graph_dialog import GraphDialog
from validol.view.menu.main_window import Window
from validol.view.menu.table_dialog import TableDialog
from validol.view.table.tables import Table
from validol.view.view_element import ViewElement
from validol.view.menu.pdf_helper_dialog import PdfHelperDialog
from validol.view.menu.glued_active_dialog import GluedActiveDialog
from validol.view.menu.pattern_edit_dialog import PatternEditDialog
from validol.view.menu.scheduler_dialog import SchedulerDialog
from validol.view.tray import MySystemTrayIcon
from validol.view.utils.qcron import QCron
from validol.view.utils.utils import display_error


class ViewLauncher(ViewElement):
    FLAGS = QtCore.Qt.Window

    def __init__(self, controller_launcher, model_launcher):
        ViewElement.__init__(self, controller_launcher, model_launcher)

        self.app = QtWidgets.QApplication(sys.argv)

        self.app.setQuitOnLastWindowClosed(False)

        self.app_icons = self.get_icons()
        self.app.setWindowIcon(self.app_icons['default'])

        self.system_tray_icon = MySystemTrayIcon(self.app_icons['default'],
                                                 self.controller_launcher, self.model_launcher)

        self.main_window = Window(self.app, self.controller_launcher, self.model_launcher)

        self.windows = []
        self.qcrons = []

        self.refresh_schedulers()

    def mark_update_required(self):
        self.app.setWindowIcon(self.app_icons['red'])
        self.system_tray_icon.setIcon(self.app_icons['red'])
        self.main_window.show_update_button()

    def event_loop(self):
        sys.exit(self.app.exec())

    def show_main_window(self):
        self.main_window.showMaximized()

    def get_icons(self):
        resolution = re.compile('^(\d+)x(\d+)(.*)?.png$')
        app_icons = defaultdict(QtGui.QIcon)
        icons_dir = '../validol/view/icons'

        for icon in os.listdir(icons_dir):
            match = resolution.match(icon)
            x, y, name = int(match.group(1)), int(match.group(2)), match.group(3)

            app_icons[name].addFile(os.path.join(icons_dir, icon), QtCore.QSize(x, y))

        return app_icons

    def refresh_prices(self):
        self.main_window.set_cached_prices()

    def show_table(self, df, labels, title):
        self.windows.append(Table(ViewLauncher.FLAGS, df, labels, title))

    def show_graph_dialog(self, df, table_pattern, title):
        self.windows.append(GraphDialog(ViewLauncher.FLAGS, df, table_pattern, title, self.controller_launcher,
                           self.model_launcher))

    def show_graph(self, df, pattern, table_labels, title):
        self.windows.append(CheckedGraph(ViewLauncher.FLAGS, df, pattern, table_labels, title))

    def refresh_tables(self):
        self.main_window.tipped_list.refresh()

    def show_table_dialog(self):
        self.windows.append(TableDialog(ViewLauncher.FLAGS, self.controller_launcher, self.model_launcher))

    def show_pdf_helper_dialog(self, processors, widgets):
        return PdfHelperDialog(processors, widgets).get_data()

    def refresh_actives(self):
        self.main_window.flavor_chosen()

    def get_chosen_actives(self):
        return self.main_window.chosen_actives

    def ask_name(self):
        return GluedActiveDialog().get_data()

    def edit_pattern(self, json_str):
        return PatternEditDialog(json_str).get_data()

    def on_main_window_close(self):
        for window in self.windows:
            window.close()

        self.windows = []

    def quit(self):
        self.app.quit()

    @staticmethod
    def show_update_result(result):
        source, (begin, end) = result

        return '{}: {} - {}'.format(source, begin, end)

    def notify_update(self, results):
        if results:
            message = '\n'.join(map(ViewLauncher.show_update_result, results))
            self.system_tray_icon.showMessage('Update', message)

    def refresh_schedulers(self):
        schedulers = [scheduler for scheduler in self.model_launcher.read_schedulers()
                      if scheduler.working]

        update_manager = self.model_launcher.get_update_manager()

        for qcron in self.qcrons:
            qcron.stop()

        self.qcrons = [QCron(scheduler.cron, lambda: self.update_wrapper(update_manager, scheduler.name))
                       for scheduler in schedulers]

    def notify(self, message):
        self.system_tray_icon.showMessage('Message', message)

    def show_scheduler_dialog(self):
        self.windows.append(SchedulerDialog(self.controller_launcher, self.model_launcher))

    def update_wrapper(self, update_manager, source):
        if update_manager.verbose(source):
            self.notify('Update of {} started'.format(source))

        try:
            results = update_manager.update_source(source)
        except requests.exceptions.ConnectionError:
            if update_manager.verbose(source):
                self.notify('Update of {} failed due to network error'.format(source))
            return

        if update_manager.verbose(source):
            self.notify_update(results)

    def display_error(self, title, error):
        display_error(title, error)