from pyhap.accessory import Accessory
from pyhap.const import CATEGORY_TELEVISIO
import logging

class TV(Accessory):

    category = CATEGORY_TELEVISION

    NAME = 'Sharp NEC TV'
    SOURCES = {
        'HDMI 1': 3,
        'HDMI 2': 3,
        'HDMI 3': 3,
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

    def _on_active_identifier_changed(self, value):
        logger.debug('Change input to %s' % list(self.SOURCES.keys())[value-1])

    def _on_remote_key(self, value):
        logger.debug('Remote key %d pressed' % value)
        #  "Rewind": 0,
        #  "FastForward": 1,
        #  "NextTrack": 2,
        #  "PreviousTrack": 3,
        #  "ArrowUp": 4,
        #  "ArrowDown": 5,
        #  "ArrowLeft": 6,
        #  "ArrowRight": 7,
        #  "Select": 8,
        #  "Back": 9,
        #  "Exit": 10,
        #  "PlayPause": 11,
        #  "Information": 15

    def _on_mute(self, value):
        logger.debug('Mute' if value else 'Unmute')

    def _on_volume_selector(self, value):
        logger.debug('%screase volume' % ('In' if value == 0 else 'De'))


def main():
    import logging
    import signal

    from pyhap.accessory_driver import AccessoryDriver

    logging.basicConfig(level=logging.DEBUG)

    driver = AccessoryDriver(port=51826)
    accessory = TV(driver, 'TV')
    driver.add_accessory(accessory=accessory)

    signal.signal(signal.SIGTERM, driver.signal_handler)
    driver.start()


if __name__ == '__main__':
    main()
