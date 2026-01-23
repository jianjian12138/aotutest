I will implement the **Device Management** module and **Playwright Data Collection** feature as follows:

### 1. Device Management Module
**Backend (`apps/ui_automation`)**:
*   **Model**: Add `UiDevice` to `models.py` with fields: `name`, `device_id` (unique serial), `platform` (Android/iOS), `type` (Real/Emulator), `status` (Online/Offline/Busy), `remote_url`, `last_seen`.
*   **Utility**: Create `utils/device_manager.py` to handle `adb` (Android) and `idevice_id` (iOS) commands for device discovery and connection.
*   **API**:
    *   Create `UiDeviceSerializer` in `serializers.py`.
    *   Create `UiDeviceViewSet` in `views.py` with actions:
        *   `list`: Get all devices.
        *   `refresh`: Trigger a scan of connected devices and update the database.
        *   `connect`: Connect to a remote device (e.g., `adb connect`).
        *   `disconnect`: Disconnect a device.
    *   Register `devices` endpoint in `urls.py`.

**Frontend (`frontend/src/views/ui-automation`)**:
*   **Page**: Create `device/DeviceManager.vue` to list devices with status indicators and control buttons (Refresh, Connect, Disconnect).
*   **Route**: Add `/ui-automation/devices` to the router.
*   **API**: Update `api/ui_automation.js` with device management endpoints.

### 2. Playwright Data Collection Upgrade
**Backend (`apps/ui_automation`)**:
*   **Models**:
    *   Update `UiProject`: Add `debug_config` (JSONField) to store the `STEP_CAPTURE` configuration.
    *   Update `TestCaseStep`: Add `enable_debug_capture` (BooleanField) to allow enabling capture per step.
*   **Execution Logic (`test_executor.py`)**:
    *   Update `execute_step_playwright` method in `TestExecutor` class.
    *   Implement `capture_debug_data(page, timing, items)` method to collect:
        *   `annotated` (screenshot with annotations), `dom` (snapshot), `dropdown` (options), `elements` (list), `iframes`, `logs` (console), `text_candidates`.
    *   Add logic to check `enable_debug_capture` flag and `debug_config` settings.
    *   Store collected data in `media/debug_data/{project_id}/{case_id}/{step_id}_{timestamp}.json`.

**Frontend (`frontend/src/views/ui-automation`)**:
*   **Test Case Editor**: Update `TestCaseManager.vue` (Step editing section) to include a switch for "Enable Debug Capture" (Enable Data Collection).
*   **Project Config**: Ensure project update forms allow editing `debug_config` (or provide a default).

### Implementation Steps
1.  **Backend Models**: Add `UiDevice` and update `UiProject`/`TestCaseStep`. Run migrations.
2.  **Backend Logic**: Implement `DeviceManager` utility and update `TestExecutor`.
3.  **Backend API**: Create ViewSets and Serializers for devices.
4.  **Frontend**: Create Device Management page and update Test Case Step editor.
5.  **Verification**: Verify device scanning and data collection during Playwright execution.