#!/usr/bin/python
# -*- coding: utf-8 -*-
from os import path
import socket, sys, os, re, random, time, datetime
from PyQt5 import uic, QtGui, QtCore, QtWidgets
import sqlite3 as lite
# from aescipher import AESCipher
import multiprocessing
import threading
from PyQt5.QtCore import pyqtSignal
import json, khotrungquoc
try:
    from tool import vcb
except Exception:
    import vcb


#############################Main
class MainWindow(QtWidgets.QMainWindow):
    finish_check_update = pyqtSignal(int, float, str, str)

    def __init__(self):
        super(MainWindow, self).__init__()

        # var init
        self.lastFilePath = '';
        self.formSeting = None;
        self.loginThread = None;
        self.initUI()
        ## check for update
        self.new_version = ''
        self.update_mess = ''
        self.update_link = ''
        # self.check_update()
        # self.finish_check_update.connect(self.write_update_message)

    def initUI(self):


        self.tabbedViewWidget = QtWidgets.QTabWidget(self);

        # self.maidzocalculator = Maidzocalculator(self);
        #
        # self.maidzosite = Maidzosite(self);

        self.bankbot = BankBot(self);
        self.kuaidi = KuaidiBot(self);
        self.tabbedViewWidget.addTab(self.kuaidi, QtGui.QIcon(appFolderPath + '/img/post.png'), "Kuaidi Bot");
        self.tabbedViewWidget.addTab(self.bankbot, QtGui.QIcon(appFolderPath + '/img/post.png'), "Bank Bot");

        self.setCentralWidget(self.tabbedViewWidget);

        exitAction = QtWidgets.QAction(QtGui.QIcon(appFolderPath + '/img/exit.png'), "Exit", self)
        exitAction.setShortcut('Alt+Q')
        exitAction.setStatusTip("Exit application")
        exitAction.triggered.connect(self.close)

        menubar = self.menuBar()
        # OSX dummy menu
        if sys.platform == 'darwin':
            dummyMenu = menubar.addMenu("Dummy");
            dummyMenu.addAction(exitAction);

        fileMenu = menubar.addMenu("File");
        fileMenu.addAction(exitAction);

        # toolbar
        toolbar = self.addToolBar("Toolbar");
        # open at center
        width, height = 1280, 800;
        screenRect = QtWidgets.QDesktopWidget().availableGeometry();
        x, y = (
            (screenRect.width() - screenRect.x() - width) / 2, (screenRect.height() - screenRect.y() - height) / 2);
        self.setGeometry(int(x), int(y), width, height);
        self.setWindowTitle("Tập đoàn buôn lậu");
        self.setWindowIcon(QtGui.QIcon(appFolderPath + '/icon.jpg'))
        self.Msgbox = QtWidgets.QMessageBox(self)

        self.show()

    def close(self):
        for p in multiprocessing.active_children():
            p.terminate();
            p.join();
        QtWidgets.QApplication.instance().quit()

class KuaidiBotThread(QtCore.QThread):
    trigger = pyqtSignal(str, str)
    def __init__(self, mainWindow, site,path):
        QtCore.QThread.__init__(self);
        self.mainWindow = mainWindow;
        self.site = site;
        self.path = path


    def run(self):
        # while 1:
        # maidzofunction = vcb.VCB()
        #self.emit(QtCore.SIGNAL('update(QString,QString)'), "export_done", 'done!')
        email = None
        password = None
        account_number = None
        url = None
        token = None
        if self.site:
            khutrungquoc = khotrungquoc.Khotrungquoc(appFolderPath=appFolderPath, site=url, trigger=self.trigger)
            khutrungquoc.sync_images(path=self.path)
            # vcb_tool.site_login()
            # vcb_tool.get_transaction()

class KuaidiBot(QtWidgets.QWidget):
    def __init__(self, mainWindow):
        super(KuaidiBot, self).__init__();
        self.mainWindow = mainWindow;
        uic.loadUi(appFolderPath + '/ui/kuaidi.ui', self);
        self.menu = QtWidgets.QMenu(self)
        self.lastPath = ""
        self.theard_order = []
        self.pushButtonStart.clicked.connect(self.start_bot)
        self.ButtonSelectPath.clicked.connect(self.selectPathUpload)
        self.pushButtonReload.clicked.connect(self.show_kuaidi_table)
        self.pushButtonFind.clicked.connect(self.find_kuaidi_table)

        self.tableWidgetReport.verticalHeader().setVisible(False)
        self.tableWidgetReport.resizeColumnsToContents()
        self.tableWidgetReport.setSortingEnabled(True)
        self.tableWidgetReport.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.tableWidgetReport.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.tableWidgetReport.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.show_kuaidi_table()
        self.loadLastPath()
        self.lineEditPathKuaidi.setText(self.lastPath)
    
    def loadLastPath(self):
        try:
            r = open('lastPath.txt','r',encoding="utf-8")
            self.lastPath = r.read()
            r.close()
        except:
            self.saveLastPath()
    def saveLastPath(self):
        r = open('lastPath.txt','w',encoding="utf-8")
        r.write(self.lastPath)
        r.close()
    def selectPathUpload(self):
        self.lastPath = QtWidgets.QFileDialog.getExistingDirectory(self, "Select path to upload!", self.lastPath);
        print(self.lastPath)
        self.lineEditPathKuaidi.setText(self.lastPath)
        self.saveLastPath()

    def start_bot(self):
        print ('==get data==')

        site = self.comboBoxSite.currentText()
        path = self.lineEditPathKuaidi.text()
        if path.find('/') == -1:
            QtWidgets.QMessageBox.about(self, "通知", "要选择链接")
            return
        print(site,path)
        # if site:
        self.getdataThread = KuaidiBotThread(self, site,path);
        self.getdataThread.trigger.connect(self.threadUpdate)
        self.getdataThread.start();
        

        QtWidgets.QMessageBox.about(self, "通知", "已经运行")

    def save_to_database(self, table='', database=''):
        print ('okodsad')

    def createActions(self):
        ## cc action
        self.exportselectCC = QtWidgets.QAction("Export Selected Row To Text", self,
                                            shortcut="",
                                            statusTip="Export Selected Row To Text",
                                            triggered=self.export_cc_status_selectrow)
        self.checkselectCC = QtWidgets.QAction("Check CCN gate 4 Selected Row", self,
                                           shortcut="",
                                           statusTip="Check Status Selected Row",
                                           triggered=self.check_cc_status_selectrow)
        self.rmselectCC = QtWidgets.QAction("&Remove Selected Row", self,
                                        shortcut="",
                                        statusTip="Remove Selected Row", triggered=self.removeselectrowcc)
        ## shipping action
        self.rmselectshipping = QtWidgets.QAction("&Remove Selected Row", self,
                                              shortcut="",
                                              statusTip="Remove Selected Row", triggered=self.removeselectrowshipping)
    
    def contextMenuEvent(self, event):
        self.menu.exec_(event.globalPos())

    def find_kuaidi_table(self):
        self.tableWidgetReport.setRowCount(0)
        findText = self.cbfind.currentText()
        con_bill = lite.connect(appFolderPath + '/kuaidi.db')
        with con_bill:
            con_bill.row_factory = lite.Row
            cur = con_bill.cursor()
            try:
                cur.execute("SELECT * from kuaidi WHERE number LIKE '%s'" % (findText))
            except:
                cur.execute('''CREATE TABLE kuaidi
                        (id INTEGER PRIMARY KEY  AUTOINCREMENT,
                        number       CHAR(255) NOT NULL,
                        url      CHAR(999) NOT NULL,
                        weight      CHAR(255) NOT NULL,
                        updated     CHAR(255) NOT NULL);''')
            rows = cur.fetchall()

            for row in rows:
                # print row
                self.add_row_to_report_kuaidi_table(row)
        con_bill.close()

    def show_kuaidi_table(self):
        self.tableWidgetReport.setRowCount(0)

        con_bill = lite.connect(appFolderPath + '/kuaidi.db')
        with con_bill:
            con_bill.row_factory = lite.Row
            cur = con_bill.cursor()
            try:
                cur.execute("SELECT * FROM kuaidi")
            except:
                cur.execute('''CREATE TABLE kuaidi
                        (id INTEGER PRIMARY KEY  AUTOINCREMENT,
                        number       CHAR(255) NOT NULL,
                        url      CHAR(999) NOT NULL,
                        weight      CHAR(255) NOT NULL,
                        updated     CHAR(255) NOT NULL);''')
            rows = cur.fetchall()

            for row in rows:
                # print row
                self.add_row_to_report_kuaidi_table(row)
        con_bill.close()


    def add_row_to_report_kuaidi_table(self, dict_infomation={}):

        row = self.tableWidgetReport.rowCount()
        self.tableWidgetReport.insertRow(row)
        self.tableWidgetReport.setItem(row, 0, QtWidgets.QTableWidgetItem(dict_infomation["number"].strip()))
        self.tableWidgetReport.setItem(row, 1, QtWidgets.QTableWidgetItem(dict_infomation["url"].strip()))
        self.tableWidgetReport.setItem(row, 2, QtWidgets.QTableWidgetItem(dict_infomation["weight"].strip()))
        self.tableWidgetReport.setItem(row, 3, QtWidgets.QTableWidgetItem(dict_infomation["updated"].strip()))

    def add_row_to_error_order_table(self, line_information=''):

        row = self.tableWidget_order_error.rowCount()
        self.tableWidget_order_error.insertRow(row)

        self.tableWidget_order_error.setItem(row, 0, QtWidgets.QTableWidgetItem(str(row+1).strip()))
        self.tableWidget_order_error.setItem(row, 1, QtWidgets.QTableWidgetItem(str(line_information).strip()))

    def removerow(self, rows, database='', table=None):
        if table == 'billing':
            con = lite.connect(appFolderPath + '/billing/' + database)
        elif table == 'shipping':
            con = lite.connect(appFolderPath + '/shipping/' + database)
        with con:

            con.row_factory = lite.Row

            cur = con.cursor()
            i = 0
            while i < len(rows):
                r = rows[i].row()
                if table == 'billing':
                    info_id = self.cctableWidget.item(r, 0).text()
                    cur.execute("DELETE FROM billing_info WHERE id=%d" % (int(info_id)))
                elif table == 'shipping':
                    info_id = self.shippingtableWidget.item(r, 0).text()
                    cur.execute("DELETE FROM shipping_info WHERE id=%d" % (int(info_id)))
                i += 1
            con.commit()
        con.close()
        if table == 'billing':
            self.show_billing_combox_list()
        elif table == 'shipping':
            self.show_shipping_combox_list()

    def threadUpdate(self, tag, data):
        link = str(data);
        if tag == 'reload':
            # print link
            self.show_kuaidi_table();


class BankBot(QtWidgets.QMainWindow):
    def __init__(self, mainWindow):
        super(BankBot, self).__init__();
        self.mainWindow = mainWindow;
        uic.loadUi(appFolderPath + '/ui/bank.ui', self);
        self.menu = QtWidgets.QMenu(self)

        self.theard_order = []
        self.pushButtonStart.clicked.connect(self.start_bot)

        self.tableWidgetReport.verticalHeader().setVisible(False)
        self.tableWidgetReport.resizeColumnsToContents()
        self.tableWidgetReport.setSortingEnabled(True)
        self.tableWidgetReport.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.tableWidgetReport.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.tableWidgetReport.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)


    def start_bot(self):
        print ('get data')
        # get drop and item
        self.tableWidgetReport.setRowCount(0)
        # self.tableWidget_order_error.setRowCount(0)
        site = str(self.comboBoxSite.currentText())
        print(site)
        # if site:
        self.getdataThread = BankBotThread(self, site);
        self.getdataThread.start();
        #     if self.getdataThread:
        #         self.theard_order.append(self.getdataThread)
        #         self.connect(self.getdataThread, QtCore.pyqtSignal("update(QString,QString)"), self.threadUpdate);
    def save_to_database(self, table='', database=''):
        print ('okodsad')

    def createActions(self):
        ## cc action
        self.exportselectCC = QtWidgets.QAction("Export Selected Row To Text", self,
                                            shortcut="",
                                            statusTip="Export Selected Row To Text",
                                            triggered=self.export_cc_status_selectrow)
        self.checkselectCC = QtWidgets.QAction("Check CCN gate 4 Selected Row", self,
                                           shortcut="",
                                           statusTip="Check Status Selected Row",
                                           triggered=self.check_cc_status_selectrow)
        self.rmselectCC = QtWidgets.QAction("&Remove Selected Row", self,
                                        shortcut="",
                                        statusTip="Remove Selected Row", triggered=self.removeselectrowcc)
        ## shipping action
        self.rmselectshipping = QtWidgets.QAction("&Remove Selected Row", self,
                                              shortcut="",
                                              statusTip="Remove Selected Row", triggered=self.removeselectrowshipping)
    def contextMenuEvent(self, event):
        self.menu.exec_(event.globalPos())

    def add_row_to_report_order_table(self, dict_infomation={}):

        row = self.tableWidget_report_order.rowCount()
        self.tableWidget_report_order.insertRow(row)

        self.tableWidget_report_order.setItem(row, 0, QtWidgets.QTableWidgetItem(str(dict_infomation['dathang_email']).strip()))
        self.tableWidget_report_order.setItem(row, 1, QtWidgets.QTableWidgetItem(str(dict_infomation['total_qty_buy']).strip()+'/'+str(dict_infomation['total_order']).strip()))
        self.tableWidget_report_order.setItem(row, 2, QtWidgets.QTableWidgetItem(str(float(dict_infomation['total_product_price'])).strip()))
        self.tableWidget_report_order.setItem(row, 3, QtWidgets.QTableWidgetItem(str(float(dict_infomation['total_purchased_price'])).strip()))
        self.tableWidget_report_order.setItem(row, 4, QtWidgets.QTableWidgetItem(str(float(dict_infomation['check_lech_dathang'])).strip()))
        self.tableWidget_report_order.setItem(row, 5, QtWidgets.QTableWidgetItem(str(float(dict_infomation['total_shipping_price'])).strip()))
        self.tableWidget_report_order.setItem(row, 6, QtWidgets.QTableWidgetItem(str(dict_infomation['total_order_error']).strip()))
    def add_row_to_error_order_table(self, line_information=''):

        row = self.tableWidget_order_error.rowCount()
        self.tableWidget_order_error.insertRow(row)

        self.tableWidget_order_error.setItem(row, 0, QtWidgets.QTableWidgetItem(str(row+1).strip()))
        self.tableWidget_order_error.setItem(row, 1, QtWidgets.QTableWidgetItem(str(line_information).strip()))

    def removerow(self, rows, database='', table=None):
        if table == 'billing':
            con = lite.connect(appFolderPath + '/billing/' + database)
        elif table == 'shipping':
            con = lite.connect(appFolderPath + '/shipping/' + database)
        with con:

            con.row_factory = lite.Row

            cur = con.cursor()
            i = 0
            while i < len(rows):
                r = rows[i].row()
                if table == 'billing':
                    info_id = self.cctableWidget.item(r, 0).text()
                    cur.execute("DELETE FROM billing_info WHERE id=%d" % (int(info_id)))
                elif table == 'shipping':
                    info_id = self.shippingtableWidget.item(r, 0).text()
                    cur.execute("DELETE FROM shipping_info WHERE id=%d" % (int(info_id)))
                i += 1
            con.commit()
        con.close()
        if table == 'billing':
            self.show_billing_combox_list()
        elif table == 'shipping':
            self.show_shipping_combox_list()

    def threadUpdate(self, tag, data):
        link = str(data);
        if tag == 'total_product_price':
            # print link
            self.label_productionprice.setText(link);
        if tag == 'total_purchased_price':
            self.label_paidproduction.setText(link)
            # print link
        if tag == 'total_shipping_price':
            self.label_totalshipping.setText(link)
        if tag == 'total_service_price':
            self.label_totalservices.setText(link)
        if tag == 'total_gains':
            self.label_gains.setText(link)
        if tag == 'total_chenhlech':
            self.label_totalchechlenh.setText(link)
        if tag == 'total_order_error':
            self.label_ordererror.setText(link)
        if tag == 'total_quantity':
            self.label_totalquatity.setText(link)
        if tag == 'total_list_info_dathang':
            dict_dathang_info = eval(link)
            for line_dathang_info in dict_dathang_info:
                self.add_row_to_report_order_table(dict_dathang_info[line_dathang_info])
            # print dict_dathang_info
        if tag == 'total_order_wrong':
            list_order_wrong = eval(link)
            for line_order_wrong in list_order_wrong:
                self.add_row_to_error_order_table(line_order_wrong)
            # print list_order_wrong
        if tag == 'update_status':
            self.label_process.setText(link)
        if tag == 'total_chenhlech_chuaup':
            print (link)

class BankBotThread(QtCore.QThread):
    def __init__(self, mainWindow, site):
        QtCore.QThread.__init__(self);
        self.mainWindow = mainWindow;
        self.site = site;

    def run(self):
        # while 1:
        # maidzofunction = vcb.VCB()
        #self.emit(QtCore.SIGNAL('update(QString,QString)'), "export_done", 'done!')
        email = None
        password = None
        account_number = None
        url = None
        token = None
        if self.site == 'Maidzo':
            email = '0948002324'
            password = 'Ttbd123!@#'
            account_number = '0451000349077'
            url = 'https://maidzo.vn/page/import_vcb_transaction/'
            token = 'a6280f7708d7fa9ced8101d58cff6e9cc2831baf'
        elif self.site == 'Shipway247':
            email = '0705891987'
            password = 'Hanoi1234@#'
            account_number = '0451000307966'
            url = 'https://shipway247.com/page/import_vcb_transaction/'
            token = 'dc9432155d351ef593f04739886473af2e8f8918'
        elif self.site == 'Chuyenhang365':
            email = '0974685613'
            password = 'Bi.280817'
            account_number = '0691000393119'
            url = 'https://quanly.chuyenhang365.com/page/import_vcb_transaction/'
            token = 'c3daf4be2f2365b3da8885d7d9044223a1a33e90'
        elif self.site == 'Alo68':
            email = '0904657943'
            password = 'Alo68.vn'
            account_number = '0691002933741'
            url = 'https://alo68.vn/page/import_vcb_transaction/'
            token = 'dc4fffcf58574cd3c204dff31713668dcbb9a610'   
        elif self.site == 'Vanchuyensieure':
            email = '0904652025'
            password = 'Vcsr123!@#'
            account_number = '0341007162304'
            url = 'https://vanchuyensieure.com/page/import_vcb_transaction/'
            token = 'ec417f50adeebcc18b26f53fb9018b3b05d2858f'
        elif self.site == 'Phathangsieuroc':
            email = '0936398482'
            password = 'Hanoi123!'
            account_number = '0451001608505'
            url = 'https://phathangsieutoc.com/page/import_vcb_transaction/'
            token = '9be4332e246c3aa6d1af0ea3bfe1962852ebf9af'
        elif self.site == 'Sieunhap':
            email = '0934587838'
            password = 'Sieunhap123!@#'
            account_number = '1014678222'
            url = 'https://sieunhap.com/page/import_vcb_transaction/'
            token = 'a9f5a5cfa97ca344aae655b8b99b4d41ce3ea034'

        elif self.site == 'Thegioinhaphang':
            email = '0967764404'
            password = 'HPLien2642019a@'
            account_number = '0021000322140'
            url = 'https://thegioinhaphang.com/page/import_vcb_transaction/'
            token = '9bded8c9baefac967c4aca332268609bf1b13634'
        elif self.site == 'Alochuyenhang':
            email = '0917377992'
            password = 'Ab120689'
            account_number = '0451000446181'
            url = 'https://alochuyenhang.com/page/import_vcb_transaction/'
            token = '00d641d02e6d4f11535db0ae047483b222ce1517'
        if email and password and account_number:
            vcb_tool = vcb.VCB(email, password, account_number)

            vcb_tool.scan_bank(url, token)
            # vcb_tool.site_login()
            # vcb_tool.get_transaction()

class Update_status_worker(QtCore.QThread):
    trigger = pyqtSignal(str, str)

    def __init__(self, statusqueue):
        QtCore.QThread.__init__(self)
        self.statusqueue = statusqueue

    def run(self):
        while 1:
            tag, status_recive = self.statusqueue.get()
            try:
                self.trigger.emit(tag, status_recive);
            except Exception as e:
                print(e)


def main():
    # get appFolderPath
    global appFolderPath
    try:
        import ctypes

        myappid = 'Meomun.Automator'  # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except:
        pass
    try:
        currentRunningScriptPath = os.path.realpath(__file__)
        appFolderPath, scriptName = os.path.split(currentRunningScriptPath);
    except Exception as e:
        appFolderPath = os.getcwd();  # for window build

    # load config
    # global config;
    # config = Config(appFolderPath);

    app = QtWidgets.QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon(appFolderPath + '/icon.jpg'))
    # add freeze support

    ex = MainWindow();
    result = app.exec_();

    # wait and terminate all child process
    print ('kill process')
    for p in multiprocessing.active_children():
        p.terminate();
        p.join();
    sys.exit(result)
    print ('done')


if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()

