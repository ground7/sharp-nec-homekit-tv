from pyhap.accessory import Accessory
from pyhap.const import CATEGORY_TELEVISION
import logging
logger = logging.getLogger(__name__)
from nec_pd_sdk.nec_pd_sdk import NECPD
from nec_pd_sdk.protocol import PDError
from nec_pd_sdk.constants import *
from nec_pd_sdk.opcode_decoding import *
import cec

class TV(Accessory):

    category = CATEGORY_TELEVISION

    NAME = 'Sharp NEC TV'
    SOURCES = {
        'DisplayPort': 0, # OPCODE_INPUT 15
        'HDMI 1': 1, # OPCODE_INPUT 17
        'HDMI 2': 2, # OPCODE_INPUT 18
        'Compute Module': 3, # OPCODE_INPUT 136
    }

    def __init__(self, *args, **kwargs):
        super(TV, self).__init__(*args, **kwargs)

        self.set_info_service(
            manufacturer='HaPK',
            model='Raspberry Pi',
            firmware_revision='1.0',
            serial_number='1'
        )

        tv_service = self.add_preload_service(
            'Television', ['Name',
                           'ConfiguredName',
                           'Active', # On or Off
                           'ActiveIdentifier', # Media Source
                           'RemoteKey', # iPhone Remote App
                           # 'Brightness', # OPCODE_PICTURE__BRIGHTNESS 0 to 100
                           'SleepDiscoveryMode'],
        )
        self._active = tv_service.configure_char(
            'Active', value=0,
            setter_callback=self._on_active_changed,
        )
        tv_service.configure_char(
            'ActiveIdentifier', value=1,
            setter_callback=self._on_active_identifier_changed,
        )
        tv_service.configure_char(
            'RemoteKey', setter_callback=self._on_remote_key,
        )
        tv_service.configure_char('Name', value=self.NAME)
        # TODO: implement persistence for ConfiguredName
        tv_service.configure_char('ConfiguredName', value=self.NAME)
        tv_service.configure_char('SleepDiscoveryMode', value=1)

        for idx, (source_name, source_type) in enumerate(self.SOURCES.items()):
            input_source = self.add_preload_service('InputSource', ['Name', 'Identifier'])
            input_source.configure_char('Name', value=source_name)
            input_source.configure_char('Identifier', value=idx + 1)
            # TODO: implement persistence for ConfiguredName
            input_source.configure_char('ConfiguredName', value=source_name)
            input_source.configure_char('InputSourceType', value=source_type)
            #  "Other": 0,
            #  "HomeScreen": 1,
            #  "Tuner": 2,
            #  "HDMI": 3,
            #  "CompositeVideo": 4,
            #  "SVideo": 5,
            #  "ComponentVideo": 6,
            #  "DVI": 7,
            #  "AirPlay": 8,
            #  "USB": 9,
            #  "Application": 10
            input_source.configure_char('IsConfigured', value=1)
            # Set visibility to shown
            input_source.configure_char('CurrentVisibilityState', value=0)

            tv_service.add_linked_service(input_source)

        tv_speaker_service = self.add_preload_service(
            'TelevisionSpeaker', ['Active',
                                  'VolumeControlType',
                                  'VolumeSelector']
        )
        tv_speaker_service.configure_char('Active', value=1)
        # Set relative volume control
        tv_speaker_service.configure_char('VolumeControlType', value=1)
        tv_speaker_service.configure_char(
            'Mute', setter_callback=self._on_mute,
        )
        tv_speaker_service.configure_char(
            'VolumeSelector', setter_callback=self._on_volume_selector,
        )

    def _on_active_changed(self, value):
        logger.debug('Turn %s' % ('on' if value else 'off'))
        tv = cec.Device(cec.CECDEVICE_TV)
        if value == 1:
            tv.power_on()
        elif value == 0:
            tv.standby()

    def _on_active_identifier_changed(self, value):
        logger.debug('Change input to %s' % list(self.SOURCES.keys())[value-1])
        try:
            pd = NECPD.open("192.168.0.10")
            pd.helper_set_destination_monitor_id(1)
            if value == 1:
                pd.command_set_parameter(OPCODE_INPUT, 15)  # DisplayPort
            elif value == 2:
                pd.command_set_parameter(OPCODE_INPUT, 17)  # HDMI 1
            elif value == 3:
                pd.command_set_parameter(OPCODE_INPUT, 18)  # HMDI 2
            elif value == 4:
                pd.command_set_parameter(OPCODE_INPUT, 136) # COMPUTE MODULE
        except PDError as msg:
            print("PDError:", msg)
        finally:
            pd.close()
            

    def _on_remote_key(self, value):
        logger.debug('Remote key %d pressed' % value)
        # https://github.com/Pulse-Eight/libcec/blob/master/src/pyCecClient/pyCecClient.py
        #  "Rewind": 0,
        #  "FastForward": 1,
        #  "NextTrack": 2,
        #  "PreviousTrack": 3,
        #  "ArrowUp": 4, # libcec for arrows select back exit playpause? information should be menu then
        #  "ArrowDown": 5,
        #  "ArrowLeft": 6,
        #  "ArrowRight": 7,
        #  "Select": 8,
        #  "Back": 9,
        #  "Exit": 10,
        #  "PlayPause": 11,
        #  "Information": 15 OPCODE_OSD__COMMUNICATIONS_INFORMATION
        # reply = pd.command_set_parameter(OPCODE_OSD__COMMUNICATIONS_INFORMATION, 2) # 1 2
        # logger.debug("command_set_parameter result:", reply.result, "opcode:", hex(reply.opcode), "type:", reply.type,
        #       "max_value:", reply.max_value, "current_value:", reply.current_value)

    def _on_mute(self, value):
        logger.debug('Mute' if value == 1 else 'Unmute') # OPCODE_AUDIO__MUTE or maybe OPCODE_SCREEN_MUTE 1 = mute 2 = unmute
        # reply = pd.command_set_parameter(OPCODE_AUDIO__MUTE, 2) # 1 2
        # logger.debug("command_set_parameter result:", reply.result, "opcode:", hex(reply.opcode), "type:", reply.type,
        #       "max_value:", reply.max_value, "current_value:", reply.current_value)

    def _on_volume_selector(self, value):
        logger.debug('%screase volume' % ('In' if value == 0 else 'De')) # OPCODE_AUDIO__AUDIO_VOLUME 0 to 100

def main():
    import logging
    import signal

    from pyhap.accessory_driver import AccessoryDriver

    logging.basicConfig(level=logging.DEBUG)
    cec.init()
    driver = AccessoryDriver(port=51826)
    accessory = TV(driver, 'TV')
    driver.add_accessory(accessory=accessory)
    signal.signal(signal.SIGTERM, driver.signal_handler)
    driver.start()

if __name__ == '__main__':
    main()
