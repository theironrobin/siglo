
from gi.repository import Gtk

@Gtk.Template(resource_path='/org/gnome/siglo/window.ui')
class SigloWindow(Gtk.ApplicationWindow):
    __gtype_name__ = 'SigloWindow'

    sync_button = Gtk.Template.Child()
    SigloWindow = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

