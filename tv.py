from pyhap.accessory import Accessory
from pyhap.const import CATEGORY_TELEVISION
import logging
from nec_pd_sdk.nec_pd_sdk import NECPD
from nec_pd_sdk.protocol import PDError
from nec_pd_sdk.constants import PD_IR_COMMAND_CODES, OPCODE_INPUT
from nec_pd_sdk.opcode_decoding import *

# Set up logging for the application
logger = logging.getLogger(__name__)

class TV(Accessory):
    # Define the category for the accessory (Television)
    category = CATEGORY_TELEVISION

    # TV specific information and input source definitions
    NAME = 'Sharp NEC TV'
    SOURCES = {
        'DisplayPort': 0, # Category Other
        'HDMI 1': 3, # Category HDMI
        'HDMI 2': 3,
        'Compute Module': 0,
    }

    def __init__(self, *args, **kwargs):
        # Call the parent class constructor to initialize the accessory
        super(TV, self).__init__(*args, **kwargs)

        # Initialize the connection to the NEC PD device (TV)
        self.pd = NECPD.open("192.168.2.84")
        self.pd.helper_set_destination_monitor_id(1)
        self.firmware = self.pd.command_firmware_version_read(0) # 0,1,2,3,4 five stored firmware versions - just get first

        # Set up accessory info (e.g., manufacturer, model, serial number)
        self.set_info_service(
            manufacturer='Sharp NEC',
            model=self.pd.command_model_name_read(),
            firmware_revision='1.0', #self.firmware[0],
            serial_number=self.pd.command_serial_number_read()
        )

        # Configure the TV service (power, input source, remote key, etc.)
        tv_service = self.add_preload_service(
            'Television', 
            ['Active', 'ActiveIdentifier', 'RemoteKey', 'Name', 'ConfiguredName', 'SleepDiscoveryMode']
        )

        # Set up character for 'Active' (power state)
        self.active_tv_service = tv_service.configure_char('Active', value=0, setter_callback=self._on_active_changed, getter_callback=self._get_power_status)
        
        # Set up character for 'ActiveIdentifier' (current input source)
        self.activeidentifier_tv_service = tv_service.configure_char('ActiveIdentifier', value=1, setter_callback=self._on_active_identifier_changed, getter_callback=self._get_current_input)
        
        # Set up character for 'RemoteKey' (handling apple remote app key presses)
        self.remotekey = tv_service.configure_char('RemoteKey', setter_callback=self._on_remote_key)
        
        # Set TV name and configured name
        self.name_tv_service = tv_service.configure_char('Name', value=self.NAME)
        self.configuredname_tv_service = tv_service.configure_char('ConfiguredName', value=self.NAME)
        
        # Sleep Discovery Mode configuration (set to 1)
        self.sleepdiscoverymode = tv_service.configure_char('SleepDiscoveryMode', value=1)

        # Configure input sources (DisplayPort, HDMI, etc.)
        for idx, (source_name, source_type) in enumerate(self.SOURCES.items()):
            input_source = self.add_preload_service('InputSource', ['Name', 'Identifier'])
            input_source.configure_char('Name', value=source_name)
            input_source.configure_char('Identifier', value=idx + 1)
            input_source.configure_char('ConfiguredName', value=source_name)
            input_source.configure_char('InputSourceType', value=source_type)
            input_source.configure_char('IsConfigured', value=1)  # Mark input as configured
            input_source.configure_char('CurrentVisibilityState', value=0)  # Set visibility to shown
            tv_service.add_linked_service(input_source)

        # Configure TV Speaker Service (Mute, Volume Control, etc.)
        tv_speaker_service = self.add_preload_service('TelevisionSpeaker', ['Active', 'VolumeControlType', 'Mute', 'VolumeSelector'])
        self.active_tv_speaker_service = tv_speaker_service.configure_char('Active', value=1)
        self.volumecontroltype = tv_speaker_service.configure_char('VolumeControlType', value=1)  # Relative volume control
        self.mute = tv_speaker_service.configure_char('Mute', setter_callback=self._on_mute)
        self.volumeselector = tv_speaker_service.configure_char('VolumeSelector', setter_callback=self._on_volume_selector)

    @Accessory.run_at_interval(3)
    def run(self):
        """This method periodically updates the TV's state."""
        try:
            # Update the 'Active' state (power state)
            self.active_tv_service.set_value(self.active_tv_service.get_value())
            self.active_tv_service.notify()

            # Update the current input source
            self.activeidentifier_tv_service.set_value(self.activeidentifier_tv_service.get_value())
            self.activeidentifier_tv_service.notify()
        except Exception as e:
            logger.error(f"Error updating TV state: {e}")

    def _get_power_status(self):
        """Fetch the current power status from the TV using NEC PD."""
        try:
            value = self.pd.command_power_status_read()
            logger.debug(f'Power status: {value}')
            if value == 0: # Error
                return 0
            elif value == 1: # On
                return 1
            elif value == 2: # Standby
                return 0
            elif value == 3: # Suspend
                return 0
            elif value == 4: # Off
                return 0
        except PDError as msg:
            logger.error(f"PDError: {msg}")
        return 0

    def _get_current_input(self):
        """Fetch the current input source from the TV using NEC PD."""
        try:
            value = self.pd.command_get_parameter(OPCODE_INPUT).current_value
            logger.debug(f'Input is {value}')
            if value == 15:  # DisplayPort
                return 1
            elif value == 17:  # HDMI 1
                return 2
            elif value == 18:  # HDMI 2
                return 3
            elif value == 136:  # Compute Module
                return 4
        except PDError as msg:
            logger.error(f"PDError: {msg}")
        return 4  # Default to Compute Module if there's an error

    def _on_active_changed(self, value):
        """Callback for when the 'Active' state (power) changes."""
        logger.debug(f'Turn {"on" if value else "off"}')
        try:
            if value == 1:
                # Power on command via IR remote control
                self.pd.command_send_ir_remote_control_code(PD_IR_COMMAND_CODES.get('power_on'))
            elif value == 0:
                # Power off command via IR remote control
                self.pd.command_send_ir_remote_control_code(PD_IR_COMMAND_CODES.get('standby'))
        except PDError as msg:
            logger.error(f"PDError: {msg}")

    def _on_active_identifier_changed(self, value):
        """Callback for when the input source changes."""
        logger.debug(f'Change input to {list(self.SOURCES.keys())[value-1]}')
        try:
            if value == 1:
                self.pd.command_set_parameter(OPCODE_INPUT, 15)  # DisplayPort
            elif value == 2:
                self.pd.command_set_parameter(OPCODE_INPUT, 17)  # HDMI 1
            elif value == 3:
                self.pd.command_set_parameter(OPCODE_INPUT, 18)  # HDMI 2
            elif value == 4:
                self.pd.command_set_parameter(OPCODE_INPUT, 136)  # Compute Module
        except PDError as msg:
            logger.error(f"PDError: {msg}")

    def _on_remote_key(self, value):
        """Callback for when a remote key is pressed."""
        logger.debug(f'Remote key {value} pressed')
        try:
            # Send the appropriate IR command based on the pressed remote key
            remote_control_map = {
                4: 'up',
                5: 'down',
                6: '-',
                7: '+',
                8: 'set',
                9: 'exit', # back
                10: 'exit',
                11: 'set', # play/pause
                15: 'menu' # info
            }
            if value in remote_control_map:
                self.pd.command_send_ir_remote_control_code(PD_IR_COMMAND_CODES.get(remote_control_map[value]))
        except PDError as msg:
            logger.error(f"PDError: {msg}")

    def _on_mute(self, value):
        """Callback for mute/unmute."""
        logger.debug('Mute' if value == 1 else 'Unmute')
        try:
            self.pd.command_send_ir_remote_control_code(PD_IR_COMMAND_CODES.get('mute'))
        except PDError as msg:
            logger.error(f"PDError: {msg}")

    def _on_volume_selector(self, value):
        """Callback for volume control (increase/decrease)."""
        logger.debug(f'{"Increase" if value == 0 else "Decrease"} volume')
        try:
            volume_control_map = {
                0: 'vol+',
                1: 'vol-'
            }
            if value in volume_control_map:
                self.pd.command_send_ir_remote_control_code(PD_IR_COMMAND_CODES.get(volume_control_map[value]))
        except PDError as msg:
            logger.error(f"PDError: {msg}")

    def stop(self):
        """Close the PD connection when the accessory is stopped."""
        if hasattr(self, 'pd'):
            self.pd.close()

def main():
    """Main entry point for the accessory driver."""
    import signal
    from pyhap.accessory_driver import AccessoryDriver

    logging.basicConfig(level=logging.ERROR)
    driver = AccessoryDriver(port=51826)
    accessory = TV(driver, 'TV')
    driver.add_accessory(accessory=accessory)
    signal.signal(signal.SIGTERM, driver.signal_handler)
    driver.start()

if __name__ == '__main__':
    main()
