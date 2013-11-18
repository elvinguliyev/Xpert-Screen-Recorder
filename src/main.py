# -*- coding: utf-8 -*-
# =============================================================================
# Xpert Screen Recorder
# Copyright (C) 2013 OSMAN TUNCELLI
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
# =============================================================================
import singleton, logging
singleton.logger.setLevel(logging.CRITICAL)
singleton.SingleInstance()
import pygtk
pygtk.require('2.0')
import gtk, os, sys, subprocess, operator, signal, webbrowser
from datetime import datetime
from collections import OrderedDict
from ConfigParser import ConfigParser

DEBUG_MODE = False

if not DEBUG_MODE:
    sys.stderr = open(os.path.devnull, 'w')

LANG = 'en'
def T(s):
    dic = {'Xpert Screen Recorder'  : u'Xpert Ekran Görüntüsü Kaydedici',
           'Start Recording'        : u'Kaydı Başlat',
           'Stop Recording'         : u'Kaydı Durdur',
           'Settings'               : 'Ayarlar',
           'About'                  : u'Hakkında', 
           'Exit'                   : u'Çıkış',
           'Resolution'             : u'Çözünürlük',
           'Frame rate'             : u'Çerçeve hızı',
           'Language'               : u'Arayüz Dili',
           'Save To'                : u'Kayıt Yeri',
           'Xpert Screen Recorder is a multi-platform screencast recorder.' : u'Xpert Ekran Görüntüsü Kaydedici, ekran görüntüsünü çeşitli platformlarda kaydedebilen bir araçtır.',
           'All Done! Do you want to watch the recorded video now?' : u'Tamamlandı! Kaydedilen görüntüyü şimdi izlemek ister misiniz?' }
    return (dic[s] if LANG == 'tr' else s)

class Settings(object):
    def __init__(self, screen_size, inifile = 'settings.ini'):
        self.defaults = { 'framerate' : 30, 'resolution' : screen_size, 'saveto' : os.path.expanduser('~'), 'lang' : 'en' }
        self.active = self.defaults.copy()
        self.screen_size = screen_size
        self.dialog_shown = False
        
        self.valid_framerates = (15,25,30)
        self._set_valid_resolutions()
        self.valid_languages = OrderedDict((('en', 'English'), ('tr', u'Türkçe')))
        
        self.inifile = inifile
        self.cp = ConfigParser()
        if os.path.isfile(inifile):
            self.cp.read(inifile)
            self.correct(self.cp._defaults)
            self.active = self.cp._defaults.copy()
        else:
            self.cp._defaults = self.defaults.copy()
            with open(inifile, 'w') as fp:
                self.cp.write(fp)
            
    def correct(self, d):
        try:
            d['framerate'] = int(d['framerate'])
            assert d['framerate'] in self.valid_framerates
        except:
            d['framerate'] = self.defaults['framerate']
        
        try:
            d['resolution'] = eval(d['resolution'])
            assert d['resolution'] in self.valid_resolutions
        except:
            d['resolution'] = self.defaults['resolution']
            
        try:
            assert os.path.isdir(d['saveto'])
        except:
            d['saveto'] = self.defaults['saveto']
            
        try:
            assert d['lang'] in ('tr', 'en')
        except:
            d['lang'] = 'en'
    
    def _set_valid_resolutions(self):
        width_array = (1920, 1680, 1280, 960)
        aspect_ratio = operator.truediv(*self.screen_size)
        self.valid_resolutions = tuple((w, int(w / aspect_ratio)) for w in width_array if w <= self.screen_size[0])
        
    def set_framerate(self, framerate):
        self.active['framerate'] = int(framerate)
    
    def set_resolution(self, res):
        if isinstance(res, basestring):
            self.active['resolution'] = tuple(res.split('x'))
        else:
            self.active['resolution'] = tuple(res)
    
    def set_saveto(self, saveto):
        self.active['saveto'] = saveto
        
    def get_framerate(self):
        return self.active['framerate']
    
    def get_resolution(self):
        return self.active['resolution']
    
    def get_saveto(self):
        return self.active['saveto']
    
    def get_language(self):
        return self.active['lang']
    
    def show_dialog(self, reload_func):
        self.dialog_shown = True
        self.reload_func = reload_func
        dialog = gtk.Dialog()
        dialog.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_UTILITY)
        dialog.set_size_request(250,250)
        dialog.set_resizable(False)
        dialog.set_position(gtk.WIN_POS_CENTER)
        
        label_settings = gtk.Label()
        label_resolution = gtk.Label()
        label_framerate  = gtk.Label()
        label_language  = gtk.Label()
        
        def set_settings_texts():
            dialog.set_title(T('Settings'))
            label_settings.set_markup('<span font_family="Verdana" weight="heavy" size="x-large">' + dialog.get_title() + '</span>')
            label_resolution.set_text(T('Resolution') + ' :')
            label_framerate.set_text(T('Frame rate') + ' :')
            label_language.set_text(T('Language') + ' :')
        set_settings_texts()
        store_resolution = gtk.ListStore(str)
        store_framerate = gtk.ListStore(str)
        store_language = gtk.ListStore(str)
        for v in self.valid_languages.values():
            store_language.append([v])
        renderer = gtk.CellRendererText()
        renderer.set_alignment(1, 0.5)
        for vr in self.valid_resolutions:
            store_resolution.append(['x'.join(map(str, vr))])
        self.combo_resolution = gtk.ComboBox(store_resolution)
        self.combo_resolution.pack_start(renderer)
        self.combo_resolution.add_attribute(renderer, 'text', 0)
        self.combo_resolution.set_active(self.valid_resolutions.index(self.get_resolution()))
        for fr in self.valid_framerates:
            store_framerate.append([fr])
        self.combo_framerate = gtk.ComboBox(store_framerate)
        self.combo_framerate.pack_start(renderer)
        self.combo_framerate.add_attribute(renderer, 'text', 0)
        self.combo_framerate.set_active(self.valid_framerates.index(self.get_framerate()))
        
        self.combo_language = gtk.ComboBox(store_language)
        self.combo_language.pack_start(renderer)
        self.combo_language.add_attribute(renderer, 'text', 0)
        self.combo_language.set_active(self.valid_languages.keys().index(self.get_language()))
        
        button_browse = gtk.Button(T('Save To'))
        button_okay = gtk.Button(stock=gtk.STOCK_OK)
        button_okay.set_size_request(40, -1)        
        button_cancel = gtk.Button(stock=gtk.STOCK_CANCEL)
        button_cancel.set_size_request(40, -1)
        
        padding = 5
        table = gtk.Table(rows=3, columns=2, homogeneous=False)
        xyoptions = dict(xoptions=0, yoptions=0, xpadding=padding, ypadding=padding)
        table.attach(label_resolution, 0, 1, 0, 1, **xyoptions)
        table.attach(self.combo_resolution, 1, 2, 0, 1, xoptions=gtk.FILL|gtk.EXPAND, xpadding=padding, ypadding=padding)
        table.attach(label_framerate, 0, 1, 1, 2, **xyoptions)
        table.attach(self.combo_framerate, 1, 2, 1, 2, xoptions=gtk.FILL|gtk.EXPAND, xpadding=padding, ypadding=padding)
        table.attach(label_language, 0, 1, 2, 3, **xyoptions)
        table.attach(self.combo_language, 1, 2, 2, 3, xoptions=gtk.FILL|gtk.EXPAND, xpadding=padding, ypadding=padding)
        table.attach(button_browse, 1, 2, 3, 4, xoptions=gtk.FILL|gtk.EXPAND, xpadding=padding, ypadding=padding)
        
        vb = dialog.vbox
        vb.pack_start(label_settings, 1, 0, padding)
        vb.pack_start(table, 0, 0, padding)
        
        hb = gtk.HBox(homogeneous=False, spacing=0)
        hb.pack_start(button_okay, 1, 1, padding)
        hb.pack_start(button_cancel, 1, 1, padding)
        vb.pack_start(hb, 0, 0, padding)
        
        saveto = [self.get_saveto()]
        def on_browse(widget, saveto):
            fc = gtk.FileChooserDialog(T('Save To'), dialog, 
                                       gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER|gtk.FILE_CHOOSER_ACTION_OPEN, 
                                       (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OK, gtk.RESPONSE_OK))
            if os.path.isdir(saveto[0]):
                fc.set_current_folder(saveto[0])
            try:
                response = fc.run()
                if response == gtk.RESPONSE_OK:
                    saveto[0] = fc.get_filename()
            finally:
                fc.destroy()
                
        def on_ok(widget):
            global LANG
            LANG = self.active['lang'] = self.valid_languages.keys()[self.combo_language.get_active()]
            self.active['resolution'] = self.valid_resolutions[self.combo_resolution.get_active()]
            self.active['framerate'] = self.valid_framerates[self.combo_framerate.get_active()]
            self.active['saveto'] = saveto[0]
            self.cp._defaults = self.active.copy()
            with open(self.inifile, 'w') as fp:
                self.cp.write(fp)
            self.reload_func()
            dialog.destroy()
        
        def on_cancel(widget):
            self.active = self.cp._defaults.copy()
            dialog.destroy()

        button_browse.connect('clicked', lambda w : on_browse(w,saveto))
        button_okay.connect('clicked', on_ok)
        button_cancel.connect('clicked', on_cancel)
        
        dialog.show_all()
        dialog.present_with_time(2)
        dialog.run()
        self.dialog_shown = False

class XpertScreenRecorder(object):
    def __init__(self, indicator = None):
        global LANG
        self.app_version = "1.0"
        self.app_icon = gtk.StatusIcon()
        self.app_icon.set_from_stock(gtk.STOCK_MEDIA_PLAY)
        self.app_icon.connect('popup-menu', self.show_popup)
        self.app_icon.connect('activate', self.kill_popup)
        self.settings = Settings(self._get_screen_size())
        self.active = self.settings.active
        LANG = self.active['lang']
        self.menu = gtk.Menu()
        self.mi_rec_start = gtk.MenuItem()
        self.mi_rec_stop  = gtk.MenuItem()
        self.mi_settings  = gtk.MenuItem()
        self.mi_about     = gtk.MenuItem()
        self.mi_exit = gtk.MenuItem()
        self._reload_texts()
        self.mi_rec_start.set_sensitive(True)
        self.mi_rec_stop.set_sensitive(False)
        self.mi_rec_start.connect('activate', self.start_recording)
        self.mi_rec_stop.connect('activate', self.stop_recording)
        self.mi_settings.connect('activate', lambda _: self.settings.show_dialog(self._reload_texts))
        self.mi_about.connect('activate', self.show_about)
        self.mi_exit.connect('activate', self.exit)
        for mi in (self.mi_rec_start, self.mi_rec_stop, gtk.SeparatorMenuItem(), self.mi_settings, self.mi_about, self.mi_exit):
            self.menu.append(mi)
        self.menu.show_all()
        
        if indicator:
            indicator.set_menu(self.menu)
        self.indicator = indicator
        self._recording = False
        
    def _reload_texts(self):
        self.app_title = T('Xpert Screen Recorder')
        self.app_icon.set_tooltip_text('{} v{}'.format(self.app_title, self.app_version))
        self.mi_rec_start.set_label(T('Start Recording'))
        self.mi_rec_stop.set_label(T('Stop Recording'))
        self.mi_settings.set_label(T('Settings'))
        self.mi_about.set_label(T('About'))
        self.mi_exit.set_label(T('Exit'))
        
    def _get_screen_size(self):
        screen = self.app_icon.get_screen()
        return screen.get_width(), screen.get_height()
    
    def is_recording(self):
        return self._recording
    
    def set_recording(self, boolean):
        self._recording = boolean
        self.app_icon.set_blinking(self._recording)        
        if self._recording:
            if self.indicator:
                self.indicator.set_status(appindicator.STATUS_ATTENTION)
            self.app_icon.set_from_stock(gtk.STOCK_MEDIA_RECORD)
            self.mi_rec_start.set_sensitive(False)
            self.mi_rec_stop.set_sensitive(True)
        else:
            if self.indicator:
                self.indicator.set_status(appindicator.STATUS_ACTIVE)
            self.app_icon.set_from_stock(gtk.STOCK_MEDIA_PLAY)
            delattr(self, 'p')
            self.mi_rec_start.set_sensitive(True)
            self.mi_rec_stop.set_sensitive(False)
    
    def generate_filename(self):
        return os.path.join(self.active['saveto'], datetime.now().strftime("%Y_%m_%d_%H_%M_%S") + ".mp4")
            
    def start_recording(self, widget):
        framerate = self.active['framerate']
        rtbufsize = bufsize = 2147483647 # you can also use smaller buffer sizes
        self.filename = self.generate_filename()
        if sys.platform == 'win32': # ffmpeg for windows
            cmdline = ['ffmpeg', '-r', framerate, '-rtbufsize', rtbufsize, '-f', 'dshow',
                       '-i', 'video=screen-capture-recorder:audio=virtual-audio-capturer', '-threads', 2, 
                       '-pix_fmt', 'yuv420p','-bufsize', bufsize, '-c:v', 'libx264', 
                       '-preset', 'ultrafast', '-tune', 'zerolatency', '-threads', 2]            
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess._subprocess.STARTF_USESHOWWINDOW
        else:
            cmdline = ['avconv', '-rtbufsize', rtbufsize, '-loglevel', 'quiet', '-f', 'alsa', '-i', 'pulse', '-f', 'x11grab', 
                       '-s:v', 'x'.join(map(str, self._get_screen_size())), '-i', ':0.0', '-ar', '44100',
                       '-bufsize', bufsize, '-pix_fmt', 'yuv420p', '-c:v', 'libx264', '-c:a', 'libvo_aacenc',
                       '-preset', 'ultrafast', '-tune', 'zerolatency', '-threads', 2]
            startupinfo = None
        if not DEBUG_MODE:
            cmdline += ['-loglevel', 'quiet']
        if self.settings.screen_size <> self.active["resolution"]:
            cmdline += ['-vf', 'scale=%d:-1' %  self.active["resolution"][0], '-sws_flags', 'lanczos']
        cmdline.append(self.filename)
        cmdline = map(unicode, cmdline)
        if DEBUG_MODE:
            print ' '.join(cmdline) 
        self.p = subprocess.Popen(cmdline, stdin=subprocess.PIPE, startupinfo = startupinfo)
        self.set_recording(True)
    
    def stop_recording(self, widget):
        if not self.is_recording():
            return
        if sys.platform == 'win32':
            self.p.communicate('q\\n')
        else:
            self.p.send_signal(signal.SIGINT)
        self.p.wait()
        self.set_recording(False)
        md = gtk.MessageDialog(None, 0, gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO, T('All Done! Do you want to watch the recorded video now?'))
        md.set_position(gtk.WIN_POS_CENTER)
        response = md.run()
        md.destroy()
        if response == gtk.RESPONSE_YES:
            webbrowser.open(self.filename)

    def show_about(self, widget):
        about = gtk.AboutDialog()
        about.set_position(gtk.WIN_POS_CENTER)
        about.set_icon_name (self.app_title)
        about.set_name(self.app_title)
        about.set_version('v1.0')
        about.set_comments(T('Xpert Screen Recorder is a multi-platform screencast recorder.'))
        about.set_authors([u'Osman Tunçelli <tuncelliosman-at-gmail.com>'])
        about.run()
        about.destroy()
    
    def exit(self, widget):
        self.stop_recording(widget)
        self.app_icon.set_visible(False)
        gtk.main_quit()
    
    def kill_popup(self, widget):
        if hasattr(self, 'menu'):
            self.menu.popdown()
        
    def show_popup(self, icon, event_button, event_time):
        if not self.settings.dialog_shown:
            self.menu.popup(None, None, None if os.name == 'nt' else gtk.status_icon_position_menu,
                   event_button, event_time, self.app_icon)
        
    main = gtk.main

if __name__ == "__main__":
    indicator = None
    if sys.platform == 'linux2':
        import appindicator
        indicator = appindicator.Indicator("Xpert", "gtk-media-play-ltr", appindicator.CATEGORY_APPLICATION_STATUS)
        indicator.set_attention_icon(gtk.STOCK_MEDIA_RECORD)
        indicator.set_status(appindicator.STATUS_ACTIVE)
    app = XpertScreenRecorder(indicator)
    app.main()