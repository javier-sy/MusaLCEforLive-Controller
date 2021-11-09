from ableton.v2.control_surface import ControlSurface

from . import musa4liveosc

import importlib
import traceback
import logging
import os

# TODO: This might need fixing to work on Windows
logger = logging.getLogger("musa4liveosc")
tmp_dir = "/tmp"
log_path = os.path.join(tmp_dir, "musa4liveosc.log")
file_handler = logging.FileHandler(log_path)
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('(%(asctime)s) [%(levelname)s] %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

class Manager(ControlSurface):
    def __init__(self, c_instance):
        ControlSurface.__init__(self, c_instance)
        self.handlers = []
        self.show_message("MusaDSL for Live: Listening for OSC on port %d" % musa4liveosc.OSC_LISTEN_PORT)

        self.osc_server = musa4liveosc.OSCServer()
        self.schedule_message(0, self.tick)

        self.init_api()

    def init_api(self):
        def test_callback(params):
            self.show_message("Received OSC OK")
            self.osc_server.send("/live/test", ("ok",))
        def reload_callback(params):
            self.reload_imports()

        self.osc_server.add_handler("/live/test", test_callback)
        self.osc_server.add_handler("/live/reload", reload_callback)

        with self.component_guard():
            self.handlers = [
                musa4liveosc.ApplicationHandler(self),
                musa4liveosc.TrackHandler(self),
                musa4liveosc.SyncHandler(self)
            ]

    def clear_api(self):
        self.osc_server.clear_handlers()
        for handler in self.handlers:
            handler.clear_api()

    def tick(self):
        """
        Called once per 100ms "tick".
        Live's embedded Python implementation does not appear to support threading,
        and beachballs when a thread is started. Instead, this approach allows long-running
        processes such as the OSC server to perform operations.
        """
        logger.debug("Tick...")
        self.osc_server.process()
        self.schedule_message(1, self.tick)

    def reload_imports(self):
        try:
            importlib.reload(musa4liveosc.application)
            importlib.reload(musa4liveosc.handler)
            importlib.reload(musa4liveosc.osc_server)
            importlib.reload(musa4liveosc.track)
            importlib.reload(musa4liveosc.sync)
            importlib.reload(musa4liveosc)
        except Exception as e:
            exc = traceback.format_exc()
            logging.warning(exc)

        if self.handlers:
            self.clear_api()
            self.init_api()
        logger.info("Reloaded code")

    def disconnect(self):
        self.show_message("Disconnecting...")
        logger.info("Disconneting...")
        self.clear_api()
        self.osc_server.shutdown()
        super().disconnect()
        logger.info("...disconnected")
        self.show_message("...disconnected")
