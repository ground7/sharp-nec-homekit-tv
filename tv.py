from pyhap.accessory import Accessory
from pyhap.const import CATEGORY_TELEVISION
import logging
import cec
from nec_pd_sdk.nec_pd_sdk import NECPD
from nec_pd_sdk.protocol import PDError
from nec_pd_sdk.constants import PD_IR_COMMAND_CODES, OPCODE_INPUT
from nec_pd_sdk.opcode_decoding import *

logger = logging.getLogger(__name__)

class TV(Accessory):
    category = CATEGORY_TELEVISION

    NAME = 'Sharp NEC TV'
    SOURCES = {
        'DisplayPort': 0,  # OPCODE_INPUT 15
        'HDMI 1': 0,       # OPCODE_INPUT 17
        'HDMI 2': 0,       # OPCODE_INPUT 18
        'COMPUTE MODULE': 0,  # OPCODE_INPUT 136
    }

    def __init__(self, *args, **kwargs):
        super(TV, self).__init__(*args, **kwargs)

        self.set_info_service(
            manufacturer='Sharp NEC',
            model='Raspberry Pi CM4',
            firmware_revision='1.0',
            serial_number='1'
        )

        # Initialize NEC PD connection
        self.pd = NECPD.open("192.168.0.10")
        self.pd.helper_set_destination_monitor_id(1)

        # TV Service configuration
        tv_service = self.add_preload_service(
            'Television', ['Name',
                           'ConfiguredName',
                           'Active',  # On or Off
                           'ActiveIdentifier',  # Media Source
                           'RemoteKey',  # iPhone Remote App
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
        tv_service.configure_char('ConfiguredName', value=self.NAME)
        tv_service.configure_char('SleepDiscoveryMode', value=1)

        for idx, (source_name, source_type) in enumerate(self.SOURCES.items()):
            input_source = self.add_preload_service('InputSource', ['Name', 'Identifier'])
            input_source.configure_char('Name', value=source_name)
            input_source.configure_char('Identifier', value=idx + 1)
            input_source.configure_char('ConfiguredName', value=source_name)
            input_source.configure_char('InputSourceType', value=source_type)
            input_source.configure_char('IsConfigured', value=1)
            input_source.configure_char('CurrentVisibilityState', value=0)
            tv_service.add_linked_service(input_source)

        tv_speaker_service = self.add_preload_service(
            'TelevisionSpeaker', ['Active',
                                  'VolumeControlType',
                                  'VolumeSelector']
        )
        tv_speaker_service.configure_char('Active', value=1)
        tv_speaker_service.configure_char('VolumeControlType', value=1)
        tv_speaker_service.configure_char(
            'Mute', setter_callback=self._on_mute,
        )
        tv_speaker_service.configure_char(
            'VolumeSelector', setter_callback=self._on_volume_selector,
        )

    @Accessory.run_at_interval(3)
    def _update_tv_state(self):
        """This method periodically updates the TV's state."""
        try:
            # Update the 'Active' state (power state)
            active = self.pd.command_power_status_read()
            logger.debug('Power status: %s' % active)
            self._active.set_value(1 if active else 0) #fix?

            # Update the current input source
            current_input = self._get_current_input()
            tv_service = self.get_service('Television')
            tv_service.configure_char('ActiveIdentifier', value=current_input)
        except Exception as e:
            logger.error(f"Error updating TV state: {e}")

    def _get_current_input(self):
        """Fetch the current input source from the TV."""
        try:
            # Use the persistent PD connection to get the current input
            value = self.pd.command_get_parameter(OPCODE_INPUT)
            logger.debug('Input is %s' % value)
            if value == 15:  # DisplayPort
                return 1
            elif value == 17:  # HDMI 1
                return 2
            elif value == 18:  # HDMI 2
                return 3
            elif value == 136:  # COMPUTE MODULE
                return 4
        except PDError as msg:
            logger.error(f"PDError: {msg}")
        return 1  # Default to DisplayPort if there's an error

    def _on_active_changed(self, value):
        logger.debug('Turn %s' % ('on' if value else 'off'))
        tv = cec.Device(cec.CECDEVICE_TV)
        try:
            if value == 1:
                tv.power_on()
                self.pd.command_send_ir_remote_control_code(PD_IR_COMMAND_CODES.get('power_on'))
            elif value == 0:
                tv.standby()
                self.pd.command_send_ir_remote_control_code(PD_IR_COMMAND_CODES.get('standby'))
        except PDError as msg:
            logger.error(f"PDError: {msg}")

    def _on_active_identifier_changed(self, value):
        logger.debug('Change input to %s' % list(self.SOURCES.keys())[value-1])
        try:
            if value == 1:
                self.pd.command_set_parameter(OPCODE_INPUT, 15)  # DisplayPort
            elif value == 2:
                self.pd.command_set_parameter(OPCODE_INPUT, 17)  # HDMI 1
            elif value == 3:
                self.pd.command_set_parameter(OPCODE_INPUT, 18)  # HDMI 2
            elif value == 4:
                self.pd.command_set_parameter(OPCODE_INPUT, 136)  # COMPUTE MODULE
        except PDError as msg:
            logger.error(f"PDError: {msg}")

    def _on_remote_key(self, value):
        logger.debug('Remote key %d pressed' % value)
        try:
            if value == 4: # Up Arrow
                #self.pd.command_send_ir_remote_control_code(0x15)
                self.pd.command_send_ir_remote_control_code(PD_IR_COMMAND_CODES.get('up'))
            elif value == 5: # Down Arrow
                #self.pd.command_send_ir_remote_control_code(0x14)
                self.pd.command_send_ir_remote_control_code(PD_IR_COMMAND_CODES.get('down'))
            elif value == 6: # Left Arrow / -
                #self.pd.command_send_ir_remote_control_code(0x21)
                self.pd.command_send_ir_remote_control_code(PD_IR_COMMAND_CODES.get('-'))
            elif value == 7: # Right Arrow / +
                #self.pd.command_send_ir_remote_control_code(0x22)
                self.pd.command_send_ir_remote_control_code(PD_IR_COMMAND_CODES.get('+'))
            elif value == 8: # Set
                #self.pd.command_send_ir_remote_control_code(0x23)
                self.pd.command_send_ir_remote_control_code(PD_IR_COMMAND_CODES.get('set'))
            elif value == 9: # Exit
                #self.pd.command_send_ir_remote_control_code(0x1F)
                self.pd.command_send_ir_remote_control_code(PD_IR_COMMAND_CODES.get('exit'))
            #elif value == 11: # Play/Pause
            #    self.pd.command_send_ir_remote_control_code(0x08)
            elif value == 15: # Menu
                #self.pd.command_send_ir_remote_control_code(0x20)
                self.pd.command_send_ir_remote_control_code(PD_IR_COMMAND_CODES.get('menu'))
        except PDError as msg:
            logger.error(f"PDError: {msg}")

    def _on_mute(self, value):
        logger.debug('Mute' if value == 1 else 'Unmute')
        try:
            #self.pd.command_send_ir_remote_control_code(0x1B)
            self.pd.command_send_ir_remote_control_code(PD_IR_COMMAND_CODES.get('mute'))
        except PDError as msg:
            logger.error(f"PDError: {msg}")

    def _on_volume_selector(self, value):
        logger.debug('%screase volume' % ('In' if value == 0 else 'De'))
        try:
            if value == 0: # Increase Volume
                #self.pd.command_send_ir_remote_control_code(0x17)
                self.pd.command_send_ir_remote_control_code(PD_IR_COMMAND_CODES.get('vol+'))
            elif value == 1: # Decrease Volume
                #self.pd.command_send_ir_remote_control_code(0x16)
                self.pd.command_send_ir_remote_control_code(PD_IR_COMMAND_CODES.get('vol-'))
        except PDError as msg:
            logger.error(f"PDError: {msg}")

    def stop(self):
        """Close the PD connection when the accessory is stopped."""
        if hasattr(self, 'pd'):
            self.pd.close()

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
