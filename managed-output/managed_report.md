# eFootball 11.0.1 managed-code pass
Sun Aug 23 14:41:33 UTC 2026

## JADX status
INFO  - loading ...
INFO  - processing ...
INFO  - progress: 0 of 9679 (0%)INFO  - progress: 358 of 9679 (3%)INFO  - progress: 371 of 9679 (3%)INFO  - progress: 428 of 9679 (4%)INFO  - progress: 527 of 9679 (5%)INFO  - progress: 793 of 9679 (8%)INFO  - progress: 1192 of 9679 (12%)INFO  - progress: 1390 of 9679 (14%)INFO  - progress: 1557 of 9679 (16%)INFO  - progress: 1873 of 9679 (19%)INFO  - progress: 2201 of 9679 (22%)INFO  - progress: 2385 of 9679 (24%)INFO  - progress: 2660 of 9679 (27%)INFO  - progress: 2794 of 9679 (28%)INFO  - progress: 3043 of 9679 (31%)INFO  - progress: 3124 of 9679 (32%)INFO  - progress: 3322 of 9679 (34%)INFO  - progress: 3534 of 9679 (36%)INFO  - progress: 3760 of 9679 (38%)INFO  - progress: 4011 of 9679 (41%)INFO  - progress: 4341 of 9679 (44%)INFO  - progress: 4499 of 9679 (46%)INFO  - progress: 4599 of 9679 (47%)INFO  - progress: 4778 of 9679 (49%)INFO  - progress: 4939 of 9679 (51%)INFO  - progress: 5023 of 9679 (51%)INFO  - progress: 5060 of 9679 (52%)INFO  - progress: 5142 of 9679 (53%)INFO  - progress: 5177 of 9679 (53%)INFO  - progress: 5291 of 9679 (54%)INFO  - progress: 5396 of 9679 (55%)INFO  - progress: 5547 of 9679 (57%)INFO  - progress: 5660 of 9679 (58%)INFO  - progress: 5775 of 9679 (59%)INFO  - progress: 5898 of 9679 (60%)INFO  - progress: 6074 of 9679 (62%)INFO  - progress: 6228 of 9679 (64%)INFO  - progress: 6342 of 9679 (65%)INFO  - progress: 6571 of 9679 (67%)INFO  - progress: 6751 of 9679 (69%)INFO  - progress: 6855 of 9679 (70%)INFO  - progress: 6958 of 9679 (71%)INFO  - progress: 6973 of 9679 (72%)INFO  - progress: 7092 of 9679 (73%)INFO  - progress: 7180 of 9679 (74%)INFO  - progress: 7238 of 9679 (74%)INFO  - progress: 7277 of 9679 (75%)INFO  - progress: 7326 of 9679 (75%)INFO  - progress: 7365 of 9679 (76%)INFO  - progress: 7397 of 9679 (76%)INFO  - progress: 7502 of 9679 (77%)INFO  - progress: 7523 of 9679 (77%)INFO  - progress: 7647 of 9679 (79%)INFO  - progress: 7686 of 9679 (79%)INFO  - progress: 7697 of 9679 (79%)INFO  - progress: 7787 of 9679 (80%)INFO  - progress: 7811 of 9679 (80%)INFO  - progress: 7812 of 9679 (80%)INFO  - progress: 7920 of 9679 (81%)INFO  - progress: 7987 of 9679 (82%)INFO  - progress: 8071 of 9679 (83%)INFO  - progress: 8158 of 9679 (84%)INFO  - progress: 8315 of 9679 (85%)INFO  - progress: 8456 of 9679 (87%)INFO  - progress: 8559 of 9679 (88%)INFO  - progress: 8630 of 9679 (89%)INFO  - progress: 8672 of 9679 (89%)INFO  - progress: 8672 of 9679 (89%)INFO  - progress: 8690 of 9679 (89%)INFO  - progress: 8707 of 9679 (89%)INFO  - progress: 8740 of 9679 (90%)INFO  - progress: 8740 of 9679 (90%)INFO  - progress: 8760 of 9679 (90%)INFO  - progress: 8847 of 9679 (91%)INFO  - progress: 8853 of 9679 (91%)INFO  - progress: 8919 of 9679 (92%)INFO  - progress: 9045 of 9679 (93%)INFO  - progress: 9206 of 9679 (95%)INFO  - progress: 9314 of 9679 (96%)INFO  - progress: 9366 of 9679 (96%)INFO  - progress: 9469 of 9679 (97%)INFO  - progress: 9561 of 9679 (98%)INFO  - progress: 9626 of 9679 (99%)INFO  - progress: 9669 of 9679 (99%)INFO  - progress: 9677 of 9679 (99%)INFO  - progress: 9678 of 9679 (99%)INFO  - progress: 9678 of 9679 (99%)INFO  - progress: 9678 of 9679 (99%)INFO  - progress: 9678 of 9679 (99%)INFO  - progress: 9678 of 9679 (99%)INFO  - progress: 9678 of 9679 (99%)INFO  - progress: 9678 of 9679 (99%)                                                             ERROR - finished with errors, count: 88
JADX_FILES=14380

## Manifest peerlink activities
package=jp.konami.pesam version=11.0.1 code=311000101

ACTIVITY jp.konami.peerlink.btc.BluetoothSwitch
  exported=None
  enabled=None
  permission=None
  process=None
  launchMode=None
  theme=@android:01030010
  filters={}

ACTIVITY jp.konami.peerlink.ble.BluetoothSwitch
  exported=None
  enabled=None
  permission=None
  process=None
  launchMode=None
  theme=@android:01030010
  filters={}
## Peerlink and network glue
# jp.konami.peerlink sources

===== managed-work/jadx/sources/jp/konami/peerlink/ble/AdvertisementHeader.java =====
package jp.konami.peerlink.ble;

import java.nio.ByteBuffer;
import java.util.Arrays;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;
import java.util.UUID;
import jp.konami.Logger;
import org.json.JSONException;
import org.json.JSONObject;

/* JADX INFO: loaded from: classes3.dex */
public class AdvertisementHeader {
    private static final int MAX_CHARACTERISTIC_VALUE_LENGTH = 512;
    private static final String TAG = "AdvertisementHeader";
    private Map mAttribute;
    private String mId;
    private String mServiceId;
    private UUID mUuid;

    public AdvertisementHeader(UUID uuid, String str, String str2, Map map) {
        this.mUuid = uuid;
        this.mServiceId = str;
        this.mId = str2;
        this.mAttribute = map;
    }

    public AdvertisementHeader(byte[] bArr) throws IllegalArgumentException {
        if (deserialize(bArr)) {
            return;
        }
        clear();
        throw new IllegalArgumentException("Invalid argument.");
    }

    private boolean isValid() {
        String str;
        String str2;
        return this.mUuid != null && (str = this.mServiceId) != null && str.length() > 0 && this.mServiceId.length() <= 255 && (str2 = this.mId) != null && str2.length() > 0 && this.mId.length() <= 255;
    }

    public void clear() {
        this.mServiceId = null;
        this.mId = null;
        this.mAttribute = null;
    }

    public boolean deserialize(byte[] bArr) {
        if (bArr != null && bArr.length != 0) {
            try {
                ByteBuffer byteBufferWrap = ByteBuffer.wrap(bArr);
                long j = byteBufferWrap.getLong();
                long j2 = byteBufferWrap.getLong();
                int i = byteBufferWrap.get() & 255;
                if (i == 0) {
                    return false;
                }
                byte[] bArr2 = new byte[i];
                byteBufferWrap.get(bArr2);
                int i2 = byteBufferWrap.get() & 255;
                if (i2 == 0) {
                    return false;
                }
                byte[] bArr3 = new byte[i2];
                byteBufferWrap.get(bArr3);
                if (!byteBufferWrap.hasArray()) {
                    return false;
                }
                HashMap map = !byteBufferWrap.hasRemaining() ? null : new HashMap();
                if (map != null) {
                    JSONObject jSONObject = new JSONObject(new String(byteBufferWrap.array(), byteBufferWrap.position(), byteBufferWrap.limit() - byteBufferWrap.position()));
                    Iterator<String> itKeys = jSONObject.keys();
                    while (itKeys.hasNext()) {
                        String next = itKeys.next();
                        map.put(next, jSONObject.getString(next));
                    }
                }
                this.mUuid = new UUID(j, j2);
                this.mServiceId = new String(bArr2);
                this.mId = new String(bArr3);
                this.mAttribute = map;
                return true;
            } catch (JSONException e) {
                e.printStackTrace();
            }
        }
        return false;
    }

    public boolean equals(Object obj) {
        if (obj == null) {
            return false;
        }
        if (!(obj instanceof AdvertisementHeader)) {
            return super.equals(obj);
        }
        AdvertisementHeader advertisementHeader = (AdvertisementHeader) obj;
        UUID uuid = this.mUuid;
        if (uuid != null ? uuid.equals(advertisementHeader.mUuid) : advertisementHeader.mUuid == null) {
            String str = this.mServiceId;
            if (str != null ? str.equals(advertisementHeader.mServiceId) : advertisementHeader.mServiceId == null) {
                String str2 = this.mId;
                if (str2 != null ? str2.equals(advertisementHeader.mId) : advertisementHeader.mId == null) {
                    Map map = this.mAttribute;
                    Map map2 = advertisementHeader.mAttribute;
                    if (map == null) {
                        if (map2 == null) {
                            return true;
                        }
                    } else if (map.equals(map2)) {
                        return true;
                    }
                }
            }
        }
        return false;
    }

    public Map<String, String> getAttribute() {
        return this.mAttribute;
    }

    public String getId() {
        return this.mId;
    }

    public String getServiceId() {
        return this.mServiceId;
    }

    public UUID getUuid() {
        return this.mUuid;
    }

    public int hashCode() {
        UUID uuid = this.mUuid;
        int iHashCode = uuid == null ? 0 : uuid.hashCode();
        String str = this.mServiceId;
        int iHashCode2 = iHashCode + (str == null ? 0 : str.hashCode());
        String str2 = this.mId;
        int iHashCode3 = iHashCode2 + (str2 == null ? 0 : str2.hashCode());
        Map map = this.mAttribute;
        return iHashCode3 + (map != null ? map.hashCode() : 0);
    }

    public byte[] serialize() {
        if (!isValid()) {
            return null;
        }
        try {
            ByteBuffer byteBufferAllocate = ByteBuffer.allocate(512);
            byteBufferAllocate.putLong(this.mUuid.getMostSignificantBits());
            byteBufferAllocate.putLong(this.mUuid.getLeastSignificantBits());
            int length = this.mServiceId.length();
            if (length > 255) {
                Logger.m968e(TAG, "Unknown error.");
                return null;
            }
            byteBufferAllocate.put((byte) length);
            byteBufferAllocate.put(this.mServiceId.getBytes());
            int length2 = this.mId.length();
            if (length2 > 255) {
                Logger.m968e(TAG, "Unknown error.");
                return null;
            }
            byteBufferAllocate.put((byte) length2);
            byteBufferAllocate.put(this.mId.getBytes());
            if (this.mAttribute != null) {
                byteBufferAllocate.put(new JSONObject(this.mAttribute).toString().getBytes());
            }
            if (!byteBufferAllocate.hasArray()) {
                Logger.m968e(TAG, "Unknown error.");
                return null;
            }
            if (byteBufferAllocate.position() <= 512) {
                return Arrays.copyOfRange(byteBufferAllocate.array(), 0, byteBufferAllocate.position());
            }
            Logger.m968e(TAG, "Invalid advertise data.");
            return null;
        } catch (NullPointerException e) {
            e.printStackTrace();
            return null;
        }
    }
}

===== managed-work/jadx/sources/jp/konami/peerlink/ble/BluetoothLowEnergy.java =====
package jp.konami.peerlink.ble;

import android.app.Activity;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothManager;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import jp.konami.Logger;
import jp.konami.peerlink.ble.Central;
import jp.konami.peerlink.ble.Peripheral;

/* JADX INFO: loaded from: classes3.dex */
public class BluetoothLowEnergy {
    static final String BLUETOOTH_DEVICE_DISABLED = "JP_KONAMI_PEERLINK_BLE_BLUETOOTHLOWENERGY_BLUETOOTH_DEVICE_DISABLED";
    static final String BLUETOOTH_DEVICE_ENABLED = "JP_KONAMI_PEERLINK_BLE_BLUETOOTHLOWENERGY_BLUETOOTH_DEVICE_ENABLED";
    static final String PERMISSION_DENIED = "JP_KONAMI_PEERLINK_BLE_BLUETOOTHLOWENERGY_PERMISSION_DENIED";
    static final String PERMISSION_GRANTED = "JP_KONAMI_PEERLINK_BLE_BLUETOOTHLOWENERGY_PERMISSION_GRANTED";
    private static final String TAG = "BluetoothLowEnergy";
    private Activity mActivity;
    private BluetoothAdapter mBluetoothAdapter;
    private BluetoothManager mBluetoothManager;
    private Central mCentral;
    private Config mConfig;
    private DeviceState mDeviceState;
    private Peripheral mPeripheral;
    private Receiver mReceiver;

    public static class Config {
        private Map mAttribute;
        private String mCentralAdvertisementUuid;
        private String mDownlinkUuid;
        private String mId;
        private String mPeripheralAdvertisementUuid;
        private String mServiceId;
        private String mServiceUuid;
        private String mUplinkUuid;

        /* JADX INFO: Access modifiers changed from: private */
        public boolean isValid() {
            String str;
            String str2;
            String str3;
            String str4;
            String str5;
            String str6;
            String str7 = this.mServiceId;
            return (str7 == null || str7.isEmpty() || (str = this.mId) == null || str.isEmpty() || (str2 = this.mServiceUuid) == null || str2.isEmpty() || (str3 = this.mPeripheralAdvertisementUuid) == null || str3.isEmpty() || (str4 = this.mCentralAdvertisementUuid) == null || str4.isEmpty() || (str5 = this.mUplinkUuid) == null || str5.isEmpty() || (str6 = this.mDownlinkUuid) == null || str6.isEmpty()) ? false : true;
        }

        public Map<String, String> getAttribute() {
            return this.mAttribute;
        }

        public String getCentralAdvertisementUuid() {
            return this.mCentralAdvertisementUuid;
        }

        public String getDownlinkUuid() {
            return this.mDownlinkUuid;
        }

        public String getId() {
            return this.mId;
        }

        public String getPeripheralAdvertisementUuid() {
            return this.mPeripheralAdvertisementUuid;
        }

        public String getServiceId() {
            return this.mServiceId;
        }

        public String getServiceUuid() {
            return this.mServiceUuid;
        }

        public String getUplinkUuid() {
            return this.mUplinkUuid;
        }

        public void setAttribute(String str, String str2) {
            if (this.mAttribute == null) {
                this.mAttribute = new HashMap();
            }
            this.mAttribute.put(str, str2);
        }

        public void setCentralAdvertisementUuid(String str) {
            this.mCentralAdvertisementUuid = str;
        }

        public void setDownlinkUuid(String str) {
            this.mDownlinkUuid = str;
        }

        public void setId(String str) {
            this.mId = str;
        }

        public void setPeripheralAdvertisementUuid(String str) {
            this.mPeripheralAdvertisementUuid = str;
        }

        public void setServiceId(String str) {
            this.mServiceId = str;
        }

        public void setServiceUuid(String str) {
            this.mServiceUuid = str;
        }

        public void setUplinkUuid(String str) {
            this.mUplinkUuid = str;
        }
    }

    public enum DeviceState {
        UNSUPPORTED,
        ACTIVATING,
        ACTIVATED,
        INACTIVATING,
        INACTIVATED
    }

    private class Receiver extends BroadcastReceiver {
        private boolean mRegistered;

        public Receiver() {
            this.mRegistered = false;
            IntentFilter intentFilter = new IntentFilter();
            intentFilter.addAction(BluetoothLowEnergy.BLUETOOTH_DEVICE_ENABLED);
            intentFilter.addAction(BluetoothLowEnergy.BLUETOOTH_DEVICE_DISABLED);
            intentFilter.addAction(BluetoothLowEnergy.PERMISSION_GRANTED);
            intentFilter.addAction(BluetoothLowEnergy.PERMISSION_DENIED);
            BluetoothLowEnergy.this.mActivity.registerReceiver(this, intentFilter, 4);
            this.mRegistered = true;
        }

        public void destruct() {
            if (this.mRegistered) {
                this.mRegistered = false;
                BluetoothLowEnergy.this.mActivity.unregisterReceiver(this);
            }
        }

        protected void finalize() {
            destruct();
        }

        @Override // android.content.BroadcastReceiver
        public void onReceive(Context context, Intent intent) {
            String action = intent.getAction();
            if (action.equals(BluetoothLowEnergy.BLUETOOTH_DEVICE_ENABLED)) {
                Logger.m967d(BluetoothLowEnergy.TAG, "Bluetooth device enabled.");
                BluetoothLowEnergy.this.requestPermission();
                return;
            }
            if (action.equals(BluetoothLowEnergy.BLUETOOTH_DEVICE_DISABLED)) {
                Logger.m967d(BluetoothLowEnergy.TAG, "Bluetooth device disabled.");
                BluetoothLowEnergy.this.mDeviceState = DeviceState.INACTIVATED;
                return;
            }
            if (!action.equals(BluetoothLowEnergy.PERMISSION_GRANTED)) {
                if (action.equals(BluetoothLowEnergy.PERMISSION_DENIED)) {
                    Logger.m967d(BluetoothLowEnergy.TAG, "Permission denied.");
                    BluetoothLowEnergy.this.mDeviceState = DeviceState.INACTIVATED;
                    return;
                }
                return;
            }
            Logger.m967d(BluetoothLowEnergy.TAG, "Permission granted.");
            if (BluetoothLowEnergy.this.initPeripheral() && BluetoothLowEnergy.this.initCentral()) {
                BluetoothLowEnergy.this.mDeviceState = DeviceState.ACTIVATED;
            } else {
                Logger.m968e(BluetoothLowEnergy.TAG, "Failed to initialization.");
                BluetoothLowEnergy.this.mDeviceState = DeviceState.INACTIVATED;
            }
        }
    }

    public BluetoothLowEnergy(Config config, Activity activity) throws IllegalArgumentException {
        Activity activity2;
        this.mDeviceState = DeviceState.UNSUPPORTED;
        this.mConfig = config;
        this.mActivity = activity;
        if (!config.isValid() || (activity2 = this.mActivity) == null) {
            Logger.m968e(TAG, "Invalid argument.");
            throw new IllegalArgumentException("Invalid argument.");
        }
        if (!activity2.getPackageManager().hasSystemFeature("android.hardware.bluetooth_le")) {
            this.mDeviceState = DeviceState.UNSUPPORTED;
            return;
        }
        BluetoothManager bluetoothManager = (BluetoothManager) this.mActivity.getSystemService("bluetooth");
        this.mBluetoothManager = bluetoothManager;
        if (bluetoothManager == null) {
            this.mDeviceState = DeviceState.UNSUPPORTED;
            return;
        }
        this.mReceiver = new Receiver();
        BluetoothAdapter adapter = this.mBluetoothManager.getAdapter();
        this.mBluetoothAdapter = adapter;
        if (adapter == null || !adapter.isEnabled()) {
            this.mDeviceState = DeviceState.INACTIVATED;
            enableBluetooth();
        } else {
            this.mDeviceState = DeviceState.ACTIVATING;
            requestPermission();
        }
    }

    private void enableBluetooth() {
        if (this.mDeviceState != DeviceState.INACTIVATED) {
            return;
        }
        Intent intent = new Intent(this.mActivity, (Class<?>) BluetoothSwitch.class);
        intent.putExtra("BLUETOOTH_SWITCH", 0);
        this.mActivity.startActivity(intent);
        this.mDeviceState = DeviceState.ACTIVATING;
    }

    /* JADX INFO: Access modifiers changed from: private */
    public boolean initCentral() {
        try {
            Central.Config config = new Central.Config();
            config.setServiceId(this.mConfig.getServiceId());
            config.setId(this.mConfig.getId());
            for (Map.Entry<String, String> entry : this.mConfig.getAttribute().entrySet()) {
                config.setAttribute(entry.getKey(), entry.getValue());
            }
            config.setServiceUuid(this.mConfig.getServiceUuid());
            config.setPeripheralAdvertisementUuid(this.mConfig.getPeripheralAdvertisementUuid());
            config.setCentralAdvertisementUuid(this.mConfig.getCentralAdvertisementUuid());
            config.setUplinkUuid(this.mConfig.getUplinkUuid());
            config.setDownlinkUuid(this.mConfig.getDownlinkUuid());
            this.mCentral = new Central(config, this.mActivity);
            return true;
        } catch (Exception e) {
            e.printStackTrace();
            return false;
        }
    }

    /* JADX INFO: Access modifiers changed from: private */
    public boolean initPeripheral() {
        try {
            Peripheral.Config config = new Peripheral.Config();
            config.setServiceId(this.mConfig.getServiceId());
            config.setId(this.mConfig.getId());
            for (Map.Entry<String, String> entry : this.mConfig.getAttribute().entrySet()) {
                config.setAttribute(entry.getKey(), entry.getValue());
            }
            config.setServiceUuid(this.mConfig.getServiceUuid());
            config.setPeripheralAdvertisementUuid(this.mConfig.getPeripheralAdvertisementUuid());
            config.setCentralAdvertisementUuid(this.mConfig.getCentralAdvertisementUuid());
            config.setUplinkUuid(this.mConfig.getUplinkUuid());
            config.setDownlinkUuid(this.mConfig.getDownlinkUuid());
            this.mPeripheral = new Peripheral(config, this.mActivity);
            return true;
        } catch (Exception e) {
            e.printStackTrace();
            return false;
        }
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void requestPermission() {
        if (this.mDeviceState != DeviceState.ACTIVATING) {
            return;
        }
        Intent intent = new Intent(this.mActivity, (Class<?>) BluetoothSwitch.class);
        intent.putExtra("BLUETOOTH_SWITCH", 2);
        this.mActivity.startActivity(intent);
    }

    public void destruct() {
        Receiver receiver = this.mReceiver;
        if (receiver != null) {
            receiver.destruct();
            this.mReceiver = null;
        }
        Peripheral peripheral = this.mPeripheral;
        if (peripheral != null) {
            peripheral.destruct();
            this.mPeripheral = null;
        }
        Central central = this.mCentral;
        if (central != null) {
            central.destruct();
            this.mCentral = null;
        }
        this.mDeviceState = DeviceState.UNSUPPORTED;
    }

    public Peripheral.AdvertiseState getAdvertiseState() {
        Peripheral peripheral;
        return (this.mDeviceState != DeviceState.ACTIVATED || (peripheral = this.mPeripheral) == null) ? Peripheral.AdvertiseState.INACTIVATED : peripheral.getAdvertiseState();
    }

    public List<BluetoothLowEnergySocket> getConnectionRequestedSocketList() {
        Peripheral peripheral;
        if (this.mDeviceState != DeviceState.ACTIVATED || (peripheral = this.mPeripheral) == null) {
            return null;
        }
        return peripheral.getConnectionRequestedSocketList();
    }

    public List<BluetoothLowEnergySocket> getDetectedSocketList() {
        Central central;
        if (this.mDeviceState != DeviceState.ACTIVATED || (central = this.mCentral) == null) {
            return null;
        }
        return central.getDetectedSocketList();
    }

    public DeviceState getDeviceState() {
        return this.mDeviceState;
    }

    public Central.ScanState getScanState() {
        Central central;
        return (this.mDeviceState != DeviceState.ACTIVATED || (central = this.mCentral) == null) ? Central.ScanState.INACTIVATED : central.getScanState();
    }

    public boolean startAdvertise() {
        Peripheral peripheral;
        if (this.mDeviceState != DeviceState.ACTIVATED || (peripheral = this.mPeripheral) == null) {
            return false;
        }
        return peripheral.startAdvertise();
    }

    public boolean startScan() {
        Central central;
        if (this.mDeviceState != DeviceState.ACTIVATED || (central = this.mCentral) == null) {
            return false;
        }
        return central.startScan();
    }

    public boolean stopAdvertise() {
        Peripheral peripheral;
        if (this.mDeviceState != DeviceState.ACTIVATED || (peripheral = this.mPeripheral) == null) {
            return false;
        }
        return peripheral.stopAdvertise();
    }

    public boolean stopScan() {
        Central central;
        if (this.mDeviceState != DeviceState.ACTIVATED || (central = this.mCentral) == null) {
            return false;
        }
        return central.stopScan();
    }
}

===== managed-work/jadx/sources/jp/konami/peerlink/ble/BluetoothLowEnergySocket.java =====
package jp.konami.peerlink.ble;

import java.io.Closeable;
import java.util.Map;
import java.util.UUID;

/* JADX INFO: loaded from: classes3.dex */
public abstract class BluetoothLowEnergySocket implements Closeable {

    public static class PeerInfo {
        private Map mAttribute;
        private String mId;
        private UUID mUuid;

        public PeerInfo(UUID uuid, String str, Map map) {
            this.mUuid = uuid;
            this.mId = str;
            this.mAttribute = map;
        }

        public boolean equals(Object obj) {
            if (obj == null) {
                return false;
            }
            if (!(obj instanceof PeerInfo)) {
                return super.equals(obj);
            }
            PeerInfo peerInfo = (PeerInfo) obj;
            UUID uuid = this.mUuid;
            if (uuid != null ? uuid.equals(peerInfo.mUuid) : peerInfo.mUuid == null) {
                String str = this.mId;
                if (str != null ? str.equals(peerInfo.mId) : peerInfo.mId == null) {
                    Map map = this.mAttribute;
                    Map map2 = peerInfo.mAttribute;
                    if (map == null) {
                        if (map2 == null) {
                            return true;
                        }
                    } else if (map.equals(map2)) {
                        return true;
                    }
                }
            }
            return false;
        }

        public Map getAttribute() {
            return this.mAttribute;
        }

        public String getId() {
            return this.mId;
        }

        public UUID getUuid() {
            return this.mUuid;
        }

        public int hashCode() {
            UUID uuid = this.mUuid;
            int iHashCode = uuid == null ? 0 : uuid.hashCode();
            String str = this.mId;
            int iHashCode2 = iHashCode + (str == null ? 0 : str.hashCode());
            Map map = this.mAttribute;
            return iHashCode2 + (map != null ? map.hashCode() : 0);
        }
    }

    public enum State {
        OPEN,
        CONNECTING,
        ESTABLISHED,
        CLOSING,
        CLOSED
    }

    protected abstract void abort();

    public boolean accept() {
        return false;
    }

    @Override // java.io.Closeable, java.lang.AutoCloseable
    public abstract void close();

    public boolean connect() {
        return false;
    }

    public void destruct() {
        abort();
    }

    public abstract PeerInfo getPeerInfo();

    public abstract State getState();

    public abstract byte[] recv();

    public abstract boolean send(byte[] bArr);
}

===== managed-work/jadx/sources/jp/konami/peerlink/ble/BluetoothSwitch.java =====
package jp.konami.peerlink.ble;

import android.app.Activity;
import android.content.Intent;
import android.os.Build;
import android.os.Bundle;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;
import java.util.ArrayDeque;
import jp.konami.Logger;

/* JADX INFO: loaded from: classes3.dex */
public class BluetoothSwitch extends Activity {
    public static final int BLUETOOTH_DEVICE_OFF = 1;
    public static final int BLUETOOTH_DEVICE_ON = 0;
    public static final String BLUETOOTH_SWITCH = "BLUETOOTH_SWITCH";
    private static final int ERROR = -1;
    public static final int REQUEST_PERMISSIONS = 2;
    private static final String TAG = "ble/BluetoothSwitch";

    @Override // android.app.Activity
    protected void onActivityResult(int i, int i2, Intent intent) {
        if (i == 0) {
            sendBroadcast(new Intent(i2 == -1 ? "JP_KONAMI_PEERLINK_BLE_BLUETOOTHLOWENERGY_BLUETOOTH_DEVICE_ENABLED" : "JP_KONAMI_PEERLINK_BLE_BLUETOOTHLOWENERGY_BLUETOOTH_DEVICE_DISABLED"));
            finish();
        }
    }

    @Override // android.app.Activity
    protected void onCreate(Bundle bundle) {
        super.onCreate(bundle);
        int intExtra = getIntent().getIntExtra("BLUETOOTH_SWITCH", -1);
        if (intExtra == 0) {
            startActivityForResult(new Intent("android.bluetooth.adapter.action.REQUEST_ENABLE"), intExtra);
            return;
        }
        if (intExtra == 1) {
            Logger.m968e(TAG, "Unsupported.");
            finish();
            return;
        }
        if (intExtra != 2) {
            Logger.m968e(TAG, "Invalid request.");
            finish();
            return;
        }
        if (Build.VERSION.SDK_INT < 31) {
            ArrayDeque arrayDeque = new ArrayDeque();
            String str = new String[]{"android.permission.ACCESS_COARSE_LOCATION"}[0];
            Logger.m967d(TAG, "Check " + str + " : permission!");
            if (ContextCompat.checkSelfPermission(this, str) == -1) {
                if (ActivityCompat.shouldShowRequestPermissionRationale(this, str)) {
                    Logger.m967d(TAG, str + "priviledge UI requested!");
                }
                arrayDeque.addLast(str);
            }
            if (arrayDeque.size() != 0) {
                ActivityCompat.requestPermissions(this, (String[]) arrayDeque.toArray(new String[arrayDeque.size()]), 2);
                return;
            } else {
                sendBroadcast(new Intent("JP_KONAMI_PEERLINK_BLE_BLUETOOTHLOWENERGY_PERMISSION_GRANTED"));
                finish();
                return;
            }
        }
        String[] strArr = {"android.permission.BLUETOOTH_SCAN", "android.permission.BLUETOOTH_ADVERTISE", "android.permission.BLUETOOTH_CONNECT"};
        ArrayDeque arrayDeque2 = new ArrayDeque();
        for (int i = 0; i < 3; i++) {
            String str2 = strArr[i];
            Logger.m967d(TAG, "Check " + str2 + " : permission!");
            if (ContextCompat.checkSelfPermission(this, str2) == -1) {
                if (ActivityCompat.shouldShowRequestPermissionRationale(this, str2)) {
                    Logger.m967d(TAG, str2 + "priviledge UI requested!");
                }
                arrayDeque2.addLast(str2);
            }
        }
        if (arrayDeque2.size() == 0) {
            sendBroadcast(new Intent("JP_KONAMI_PEERLINK_BLE_BLUETOOTHLOWENERGY_PERMISSION_GRANTED"));
            finish();
        } else {
            String[] strArr2 = new String[arrayDeque2.size()];
            Logger.m967d(TAG, "request permissions! " + arrayDeque2.toString() + " priviledge UI requested!");
            ActivityCompat.requestPermissions(this, (String[]) arrayDeque2.toArray(strArr2), 2);
        }
    }

    @Override // android.app.Activity
    public void onRequestPermissionsResult(int i, String[] strArr, int[] iArr) {
        if (i == 2) {
            int i2 = 0;
            boolean z = true;
            boolean z2 = iArr.length == 0;
            int length = iArr.length;
            while (true) {
                if (i2 >= length) {
                    z = z2;
                    break;
                } else if (iArr[i2] == -1) {
                    break;
                } else {
                    i2++;
                }
            }
            if (z) {
                sendBroadcast(new Intent("JP_KONAMI_PEERLINK_BLE_BLUETOOTHLOWENERGY_PERMISSION_DENIED"));
                finish();
            } else {
                sendBroadcast(new Intent("JP_KONAMI_PEERLINK_BLE_BLUETOOTHLOWENERGY_PERMISSION_GRANTED"));
                finish();
            }
        }
    }
}

===== managed-work/jadx/sources/jp/konami/peerlink/ble/Central.java =====
package jp.konami.peerlink.ble;

import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothDevice;
import android.bluetooth.BluetoothGatt;
import android.bluetooth.BluetoothGattCallback;
import android.bluetooth.BluetoothGattCharacteristic;
import android.bluetooth.BluetoothGattDescriptor;
import android.bluetooth.BluetoothGattService;
import android.bluetooth.BluetoothManager;
import android.bluetooth.le.BluetoothLeScanner;
import android.bluetooth.le.ScanCallback;
import android.bluetooth.le.ScanFilter;
import android.bluetooth.le.ScanResult;
import android.bluetooth.le.ScanSettings;
import android.content.Context;
import android.os.ParcelUuid;
import androidx.work.WorkRequest;
import com.google.android.vending.expansion.downloader.Constants;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Queue;
import java.util.UUID;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.ConcurrentMap;
import java.util.concurrent.PriorityBlockingQueue;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicLong;
import jp.konami.Logger;
import jp.konami.peerlink.ble.BluetoothLowEnergySocket;

/* JADX INFO: loaded from: classes3.dex */
public class Central {
    private static final int ABORTING_WAIT_MS = 1500;
    private static final int CONNECTION_TIMEDOUT_MS = 60000;
    private static final int DETECTED_INFO_EXPIRE_SCAN_TIMES = 2;
    private static final int DETECTED_INFO_EXPIRE_TIME_MS = 60000;
    private static final int OPERATION_PERIOD_MIN_MS = 5000;
    private static final int OPERATION_TASK_SCAN_TIMEDOUT_MS = 30000;
    private static final int PASSIVE_SCAN_PERIOD_MS = 2000;
    private static final int SCAN_TIMEDOUT_MS = 5000;
    private static final String TAG = "Central";
    private static final int THREAD_BUSY_WAIT_SLEEP_MS = 100;
    private BluetoothAdapter mBluetoothAdapter;
    private BluetoothLeScanner mBluetoothLeScanner;
    private BluetoothManager mBluetoothManager;
    private Config mConfig;
    private Context mContext;
    private final Thread mOperationThread;
    private final ScanCallback mScanCallback;
    private ElapsedTime mScanTime;
    private State mState;
    private static final AtomicLong mNextSocketObjectId = new AtomicLong();
    private static final AtomicLong mNextSocketImplObjectId = new AtomicLong();
    private final UUID mUuid = UUID.randomUUID();
    private ScanState mScanState = ScanState.INACTIVATED;
    private final SocketMaps mSocketMaps = new SocketMaps();
    private final BlockingQueue<PriorityQueueFifoEntry<Runnable>> mOperationQueue = new PriorityBlockingQueue();

    public static class Config {
        private Map mAttribute;
        private String mCentralAdvertisementUuid;
        private String mDownlinkUuid;
        private String mId;
        private String mPeripheralAdvertisementUuid;
        private String mServiceId;
        private String mServiceUuid;
        private String mUplinkUuid;

        /* JADX INFO: Access modifiers changed from: private */
        public boolean isValid() {
            String str;
            String str2;
            String str3;
            String str4;
            String str5;
            String str6;
            String str7 = this.mServiceId;
            return (str7 == null || str7.isEmpty() || (str = this.mId) == null || str.isEmpty() || (str2 = this.mServiceUuid) == null || str2.isEmpty() || (str3 = this.mPeripheralAdvertisementUuid) == null || str3.isEmpty() || (str4 = this.mCentralAdvertisementUuid) == null || str4.isEmpty() || (str5 = this.mUplinkUuid) == null || str5.isEmpty() || (str6 = this.mDownlinkUuid) == null || str6.isEmpty()) ? false : true;
        }

        public Map<String, String> getAttribute() {
            return this.mAttribute;
        }

        public String getCentralAdvertisementUuid() {
            return this.mCentralAdvertisementUuid;
        }

        public String getDownlinkUuid() {
            return this.mDownlinkUuid;
        }

        public String getId() {
            return this.mId;
        }

        public String getPeripheralAdvertisementUuid() {
            return this.mPeripheralAdvertisementUuid;
        }

        public String getServiceId() {
            return this.mServiceId;
        }

        public String getServiceUuid() {
            return this.mServiceUuid;
        }

        public String getUplinkUuid() {
            return this.mUplinkUuid;
        }

        public void setAttribute(String str, String str2) {
            if (this.mAttribute == null) {
                this.mAttribute = new HashMap();
            }
            this.mAttribute.put(str, str2);
        }

        public void setCentralAdvertisementUuid(String str) {
            this.mCentralAdvertisementUuid = str;
        }

        public void setDownlinkUuid(String str) {
            this.mDownlinkUuid = str;
        }

        public void setId(String str) {
            this.mId = str;
        }

        public void setPeripheralAdvertisementUuid(String str) {
            this.mPeripheralAdvertisementUuid = str;
        }

        public void setServiceId(String str) {
            this.mServiceId = str;
        }

        public void setServiceUuid(String str) {
            this.mServiceUuid = str;
        }

        public void setUplinkUuid(String str) {
            this.mUplinkUuid = str;
        }
    }

    private static class ElapsedTime {
        private long mBaseTimeMs;

        public ElapsedTime() {
            reset();
        }

        public long get() {
            long jCurrentTimeMillis = System.currentTimeMillis();
            long j = this.mBaseTimeMs;
            if (jCurrentTimeMillis <= j) {
                return 0L;
            }
            return jCurrentTimeMillis - j;
        }

        public void reset() {
            this.mBaseTimeMs = System.currentTimeMillis();
        }
    }

    private static class PriorityQueueFifoEntry<T> implements Comparable<PriorityQueueFifoEntry<T>> {
        private static final AtomicLong mNextSeq = new AtomicLong();
        private final T mData;
        private final int mPriority;
        private final long mSeq = mNextSeq.getAndIncrement();

        public PriorityQueueFifoEntry(int i, T t) {
            this.mPriority = i;
            this.mData = t;
        }

        @Override // java.lang.Comparable
        public int compareTo(PriorityQueueFifoEntry<T> priorityQueueFifoEntry) {
            int i = this.mPriority;
            int i2 = priorityQueueFifoEntry.mPriority;
            return (i != i2 || this.mData == priorityQueueFifoEntry.mData) ? i < i2 ? 1 : -1 : this.mSeq < priorityQueueFifoEntry.mSeq ? -1 : 1;
        }

        public T getData() {
            return this.mData;
        }
    }

    public enum ScanState {
        ACTIVATING,
        ACTIVATED,
        INACTIVATING,
        INACTIVATED
    }

    private class Socket extends BluetoothLowEnergySocket {
        private final long mObjectId;
        private volatile SocketImpl mSocketImpl;

        private class SocketImpl {
            private static final String CONFIG_UUID = "00002902-0000-1000-8000-00805F9B34FB";
            private static final int MAX_RECV_QUEUE_SIZE = 1000;
            private static final int MAX_SEND_QUEUE_SIZE = 100;
            private static final int REQUEST_ATT_MTU = 512;
            private final BluetoothDevice mBluetoothDevice;
            private volatile BluetoothGatt mBluetoothGatt;
            private final BluetoothGattCallback mBluetoothGattCallback;
            private volatile BluetoothGattCharacteristic mDownlinkCharacteristic;
            private volatile int mMtu;
            private final long mObjectId;
            private volatile BluetoothLowEnergySocket.PeerInfo mPeerInfo;
            private Queue<byte[]> mRecvQueue;
            private Queue<byte[]> mSendQueue;
            private AtomicBoolean mSendingUplink;
            private volatile boolean mStartedConnection;
            private volatile BluetoothLowEnergySocket.State mState;
            private volatile BluetoothGattCharacteristic mUplinkCharacteristic;

            private class BluetoothGattCallbackImpl extends BluetoothGattCallback {
                private BluetoothGattCallbackImpl() {
                }

                private void readCharacteristicPeripheralAdvertisement() {
                    synchronized (SocketImpl.this) {
                        BluetoothGattService service = SocketImpl.this.mBluetoothGatt.getService(UUID.fromString(Central.this.mConfig.getServiceUuid()));
                        SocketImpl socketImpl = SocketImpl.this;
                        if (service == null) {
                            socketImpl.abort();
                            return;
                        }
                        BluetoothGattCharacteristic characteristic = service.getCharacteristic(UUID.fromString(Central.this.mConfig.getPeripheralAdvertisementUuid()));
                        SocketImpl socketImpl2 = SocketImpl.this;
                        if (characteristic == null) {
                            socketImpl2.abort();
                        } else {
                            if (socketImpl2.mBluetoothGatt.readCharacteristic(characteristic)) {
                                return;
                            }
                            SocketImpl.this.abort();
                        }
                    }
                }

                private void writeDescriptorDownlink() {
                    synchronized (SocketImpl.this) {
                        BluetoothGattService service = SocketImpl.this.mBluetoothGatt.getService(UUID.fromString(Central.this.mConfig.getServiceUuid()));
                        SocketImpl socketImpl = SocketImpl.this;
                        if (service == null) {
                            socketImpl.abort();
                            return;
                        }
                        BluetoothGattCharacteristic characteristic = service.getCharacteristic(UUID.fromString(Central.this.mConfig.getDownlinkUuid()));
                        SocketImpl socketImpl2 = SocketImpl.this;
                        if (characteristic == null) {
                            socketImpl2.abort();
                            return;
                        }
                        if (!socketImpl2.mBluetoothGatt.setCharacteristicNotification(characteristic, true)) {
                            SocketImpl.this.abort();
                            return;
                        }
                        BluetoothGattDescriptor descriptor = characteristic.getDescriptor(UUID.fromString(SocketImpl.CONFIG_UUID));
                        if (descriptor == null) {
                            SocketImpl.this.abort();
                            return;
                        }
                        boolean value = descriptor.setValue(BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE);
                        SocketImpl socketImpl3 = SocketImpl.this;
                        if (!value) {
                            socketImpl3.abort();
                            return;
                        }
                        boolean zWriteDescriptor = socketImpl3.mBluetoothGatt.writeDescriptor(descriptor);
                        SocketImpl socketImpl4 = SocketImpl.this;
                        if (zWriteDescriptor) {
                            socketImpl4.mDownlinkCharacteristic = characteristic;
                        } else {
                            socketImpl4.abort();
                        }
                    }
                }

                @Override // android.bluetooth.BluetoothGattCallback
                public void onCharacteristicChanged(BluetoothGatt bluetoothGatt, BluetoothGattCharacteristic bluetoothGattCharacteristic) {
                    synchronized (SocketImpl.this) {
                        if (!bluetoothGatt.equals(SocketImpl.this.mBluetoothGatt)) {
                            Logger.m968e(Central.TAG, "Unknown error. (mBluetoothGatt = " + SocketImpl.this.mBluetoothGatt + ", gatt = " + bluetoothGatt + ")");
                            return;
                        }
                        if (SocketImpl.this.mState == BluetoothLowEnergySocket.State.ESTABLISHED) {
                            if (SocketImpl.this.mDownlinkCharacteristic != null && bluetoothGattCharacteristic.getUuid().equals(SocketImpl.this.mDownlinkCharacteristic.getUuid())) {
                                synchronized (SocketImpl.this.mRecvQueue) {
                                    if (SocketImpl.this.mRecvQueue.size() >= 1000) {
                                        Logger.m968e(Central.TAG, "Recv queue is full.");
                                        SocketImpl.this.abort();
                                        return;
                                    } else if (!SocketImpl.this.mRecvQueue.offer(bluetoothGattCharacteristic.getValue())) {
                                        Logger.m968e(Central.TAG, "Failed to offer recv queue.");
                                        SocketImpl.this.abort();
                                        return;
                                    }
                                }
                            }
                            SocketImpl.this.abort();
                        }
                    }
                }

                @Override // android.bluetooth.BluetoothGattCallback
                public void onCharacteristicRead(BluetoothGatt bluetoothGatt, BluetoothGattCharacteristic bluetoothGattCharacteristic, int i) {
                    synchronized (SocketImpl.this) {
                        if (!bluetoothGatt.equals(SocketImpl.this.mBluetoothGatt)) {
                            Logger.m968e(Central.TAG, "Unknown error. (mBluetoothGatt = " + SocketImpl.this.mBluetoothGatt + ", gatt = " + bluetoothGatt + ")");
                            return;
                        }
                        SocketImpl socketImpl = SocketImpl.this;
                        if (i != 0) {
                            socketImpl.abort();
                            return;
                        }
                        if (socketImpl.mState == BluetoothLowEnergySocket.State.CONNECTING) {
                            if (!bluetoothGattCharacteristic.getUuid().equals(UUID.fromString(Central.this.mConfig.getPeripheralAdvertisementUuid()))) {
                                SocketImpl.this.abort();
                                return;
                            }
                            try {
                                AdvertisementHeader advertisementHeader = new AdvertisementHeader(bluetoothGattCharacteristic.getValue());
                                if (!advertisementHeader.getServiceId().equals(Central.this.mConfig.getServiceId())) {
                                    SocketImpl.this.abort();
                                    return;
                                }
                                BluetoothLowEnergySocket.PeerInfo peerInfo = new BluetoothLowEnergySocket.PeerInfo(advertisementHeader.getUuid(), advertisementHeader.getId(), advertisementHeader.getAttribute());
                                if (SocketImpl.this.mPeerInfo != null && !SocketImpl.this.mPeerInfo.equals(peerInfo)) {
                                    Logger.m968e(Central.TAG, "Unknown error.");
                                    SocketImpl.this.abort();
                                    return;
                                }
                                SocketImpl.this.mPeerInfo = peerInfo;
                                Logger.m967d(Central.TAG, "Detected peripheral. (device = " + SocketImpl.this.mBluetoothDevice.toString() + ", uuid = " + SocketImpl.this.mPeerInfo.getUuid() + ", id = " + SocketImpl.this.mPeerInfo.getId() + ", attribute = " + SocketImpl.this.mPeerInfo.getAttribute().toString() + ")");
                                boolean zIsRequestedConnection = Central.this.mSocketMaps.isRequestedConnection(SocketImpl.this.mPeerInfo.getUuid());
                                SocketImpl socketImpl2 = SocketImpl.this;
                                if (!zIsRequestedConnection) {
                                    if (Central.this.mSocketMaps.notifyDetected(SocketImpl.this.mBluetoothDevice, SocketImpl.this.mPeerInfo)) {
                                        SocketImpl.this.close();
                                        return;
                                    } else {
                                        Logger.m967d(Central.TAG, "Unknown error.");
                                        SocketImpl.this.abort();
                                        return;
                                    }
                                }
                                if (!Central.this.mSocketMaps.notifyConnected(Socket.this)) {
                                    SocketImpl.this.abort();
                                } else {
                                    Logger.m967d(Central.TAG, "Connected peripheral. (device = " + SocketImpl.this.mBluetoothDevice.toString() + ", uuid = " + SocketImpl.this.mPeerInfo.getUuid() + ", id = " + SocketImpl.this.mPeerInfo.getId() + ", attribute = " + SocketImpl.this.mPeerInfo.getAttribute().toString() + ")");
                                    writeDescriptorDownlink();
                                }
                            } catch (IllegalArgumentException e) {
                                Logger.m968e(Central.TAG, "Failed to deserialize advertisement header.");
                                e.printStackTrace();
                                SocketImpl.this.abort();
                            }
                        }
                    }
                }

                @Override // android.bluetooth.BluetoothGattCallback
                public void onCharacteristicWrite(BluetoothGatt bluetoothGatt, BluetoothGattCharacteristic bluetoothGattCharacteristic, int i) {
                    synchronized (SocketImpl.this) {
                        if (!bluetoothGatt.equals(SocketImpl.this.mBluetoothGatt)) {
                            Logger.m968e(Central.TAG, "Unknown error. (mBluetoothGatt = " + SocketImpl.this.mBluetoothGatt + ", gatt = " + bluetoothGatt + ")");
                            return;
                        }
                        SocketImpl socketImpl = SocketImpl.this;
                        if (i != 0) {
                            socketImpl.abort();
                            return;
                        }
                        if (socketImpl.mState == BluetoothLowEnergySocket.State.CONNECTING) {
                            boolean zEquals = bluetoothGattCharacteristic.getUuid().equals(UUID.fromString(Central.this.mConfig.getCentralAdvertisementUuid()));
                            SocketImpl socketImpl2 = SocketImpl.this;
                            if (!zEquals) {
                                socketImpl2.abort();
                            } else {
                                socketImpl2.mState = BluetoothLowEnergySocket.State.ESTABLISHED;
                                Logger.m967d(Central.TAG, "Established peripheral. (device = " + SocketImpl.this.mBluetoothDevice.toString() + ", uuid = " + SocketImpl.this.mPeerInfo.getUuid() + ", id = " + SocketImpl.this.mPeerInfo.getId() + ", attribute = " + SocketImpl.this.mPeerInfo.getAttribute().toString() + ")");
                            }
                        } else if (SocketImpl.this.mState == BluetoothLowEnergySocket.State.ESTABLISHED) {
                            if (SocketImpl.this.mUplinkCharacteristic != null && bluetoothGattCharacteristic.getUuid().equals(SocketImpl.this.mUplinkCharacteristic.getUuid())) {
                                SocketImpl.this.mSendingUplink.set(false);
                                SocketImpl.this.requestSend();
                            }
                            SocketImpl.this.abort();
                        }
                    }
                }

                @Override // android.bluetooth.BluetoothGattCallback
                public void onConnectionStateChange(BluetoothGatt bluetoothGatt, int i, int i2) {
                    Logger.m967d(Central.TAG, "ConnectionStateChange: gatt = " + bluetoothGatt.toString() + ", status = " + i + ", newState = " + i2);
                    synchronized (SocketImpl.this) {
                        if (!bluetoothGatt.equals(SocketImpl.this.mBluetoothGatt)) {
                            Logger.m968e(Central.TAG, "Unknown error. (mBluetoothGatt = " + SocketImpl.this.mBluetoothGatt.toString() + ", gatt = " + bluetoothGatt.toString() + ")");
                            return;
                        }
                        SocketImpl socketImpl = SocketImpl.this;
                        if (i != 0) {
                            socketImpl.abort();
                            return;
                        }
                        socketImpl.mStartedConnection = true;
                        if (i2 != 0) {
                            if (i2 != 1) {
                                if (i2 == 2) {
                                    BluetoothLowEnergySocket.State state = SocketImpl.this.mState;
                                    BluetoothLowEnergySocket.State state2 = BluetoothLowEnergySocket.State.CONNECTING;
                                    SocketImpl socketImpl2 = SocketImpl.this;
                                    if (state == state2) {
                                        if (!socketImpl2.mBluetoothGatt.requestConnectionPriority(1)) {
                                            Logger.m968e(Central.TAG, "Failed to request connection priority.");
                                        }
                                        if (!SocketImpl.this.mBluetoothGatt.discoverServices()) {
                                            Logger.m967d(Central.TAG, "Failed to discover services.");
                                            SocketImpl.this.close();
                                        }
                                    } else {
                                        socketImpl2.abort();
                                    }
                                } else if (i2 != 3) {
                                    Logger.m968e(Central.TAG, "Unknown newState of onConnectionStateChange. (newState = " + i2 + ")");
                                    SocketImpl.this.abort();
                                }
                            }
                        } else if (SocketImpl.this.mState == BluetoothLowEnergySocket.State.CLOSING || SocketImpl.this.mState == BluetoothLowEnergySocket.State.CLOSED) {
                            SocketImpl.this.mBluetoothGatt.close();
                            SocketImpl.this.mState = BluetoothLowEnergySocket.State.CLOSED;
                        } else {
                            SocketImpl.this.abort();
                        }
                    }
                }

                @Override // android.bluetooth.BluetoothGattCallback
                public void onDescriptorWrite(BluetoothGatt bluetoothGatt, BluetoothGattDescriptor bluetoothGattDescriptor, int i) {
                    synchronized (SocketImpl.this) {
                        if (!bluetoothGatt.equals(SocketImpl.this.mBluetoothGatt)) {
                            Logger.m968e(Central.TAG, "Unknown error. (mBluetoothGatt = " + SocketImpl.this.mBluetoothGatt + ", gatt = " + bluetoothGatt + ")");
                            return;
                        }
                        SocketImpl socketImpl = SocketImpl.this;
                        if (i != 0) {
                            socketImpl.abort();
                            return;
                        }
                        if (socketImpl.mState == BluetoothLowEnergySocket.State.CONNECTING) {
                            boolean zEquals = bluetoothGattDescriptor.getUuid().equals(UUID.fromString(SocketImpl.CONFIG_UUID));
                            SocketImpl socketImpl2 = SocketImpl.this;
                            if (!zEquals) {
                                socketImpl2.abort();
                                return;
                            }
                            BluetoothGattService service = socketImpl2.mBluetoothGatt.getService(UUID.fromString(Central.this.mConfig.getServiceUuid()));
                            SocketImpl socketImpl3 = SocketImpl.this;
                            if (service == null) {
                                socketImpl3.abort();
                                return;
                            }
                            BluetoothGattCharacteristic characteristic = service.getCharacteristic(UUID.fromString(Central.this.mConfig.getUplinkUuid()));
                            BluetoothGattCharacteristic characteristic2 = service.getCharacteristic(UUID.fromString(Central.this.mConfig.getCentralAdvertisementUuid()));
                            if (characteristic2 != null && characteristic != null) {
                                byte[] bArrSerialize = new AdvertisementHeader(Central.this.mUuid, Central.this.mConfig.getServiceId(), Central.this.mConfig.getId(), Central.this.mConfig.getAttribute()).serialize();
                                if (bArrSerialize == null) {
                                    SocketImpl.this.abort();
                                    return;
                                }
                                boolean value = characteristic2.setValue(bArrSerialize);
                                SocketImpl socketImpl4 = SocketImpl.this;
                                if (!value) {
                                    socketImpl4.abort();
                                    return;
                                }
                                boolean zWriteCharacteristic = socketImpl4.mBluetoothGatt.writeCharacteristic(characteristic2);
                                SocketImpl socketImpl5 = SocketImpl.this;
                                if (!zWriteCharacteristic) {
                                    socketImpl5.abort();
                                    return;
                                }
                                socketImpl5.mUplinkCharacteristic = characteristic;
                            }
                            SocketImpl.this.abort();
                        }
                    }
                }

                @Override // android.bluetooth.BluetoothGattCallback
                public void onMtuChanged(BluetoothGatt bluetoothGatt, int i, int i2) {
                    synchronized (SocketImpl.this) {
                        if (!bluetoothGatt.equals(SocketImpl.this.mBluetoothGatt)) {
                            Logger.m968e(Central.TAG, "Unknown error. (mBluetoothGatt = " + SocketImpl.this.mBluetoothGatt + ", gatt = " + bluetoothGatt + ")");
                            return;
                        }
                        if (i2 == 0) {
                            if (i <= 3) {
                                Logger.m968e(Central.TAG, "Unknown error. (mtu = " + i + ")");
                            } else {
                                SocketImpl.this.mMtu = i - 3;
                                Logger.m967d(Central.TAG, "Changed MTU. (mtu = " + SocketImpl.this.mMtu + ")");
                            }
                        }
                        if (SocketImpl.this.mPeerInfo == null) {
                            readCharacteristicPeripheralAdvertisement();
                        } else {
                            writeDescriptorDownlink();
                        }
                    }
                }

                @Override // android.bluetooth.BluetoothGattCallback
                public void onServicesDiscovered(BluetoothGatt bluetoothGatt, int i) {
                    synchronized (SocketImpl.this) {
                        if (!bluetoothGatt.equals(SocketImpl.this.mBluetoothGatt)) {
                            Logger.m968e(Central.TAG, "Unknown error. (mBluetoothGatt = " + SocketImpl.this.mBluetoothGatt + ", gatt = " + bluetoothGatt + ")");
                            return;
                        }
                        SocketImpl socketImpl = SocketImpl.this;
                        if (i != 0) {
                            socketImpl.abort();
                            return;
                        }
                        BluetoothGattService service = socketImpl.mBluetoothGatt.getService(UUID.fromString(Central.this.mConfig.getServiceUuid()));
                        SocketImpl socketImpl2 = SocketImpl.this;
                        if (service == null) {
                            socketImpl2.abort();
                            return;
                        }
                        if (socketImpl2.mPeerInfo == null) {
                            BluetoothGattCharacteristic characteristic = service.getCharacteristic(UUID.fromString(Central.this.mConfig.getPeripheralAdvertisementUuid()));
                            if (characteristic == null) {
                                SocketImpl.this.abort();
                                return;
                            }
                            List<BluetoothGattDescriptor> descriptors = characteristic.getDescriptors();
                            if (descriptors != null && !descriptors.isEmpty()) {
                                Iterator<BluetoothGattDescriptor> it = descriptors.iterator();
                                while (true) {
                                    if (!it.hasNext()) {
                                        break;
                                    }
                                    BluetoothLowEnergySocket.PeerInfo peerInfoFromDetected = Central.this.mSocketMaps.getPeerInfoFromDetected(it.next().getUuid());
                                    if (peerInfoFromDetected != null) {
                                        SocketImpl.this.mPeerInfo = peerInfoFromDetected;
                                        Logger.m967d(Central.TAG, "Detected peripheral. (device = " + SocketImpl.this.mBluetoothDevice.toString() + ", uuid = " + SocketImpl.this.mPeerInfo.getUuid() + ", id = " + SocketImpl.this.mPeerInfo.getId() + ", attribute = " + SocketImpl.this.mPeerInfo.getAttribute().toString() + ")");
                                        boolean zIsRequestedConnection = Central.this.mSocketMaps.isRequestedConnection(SocketImpl.this.mPeerInfo.getUuid());
                                        SocketImpl socketImpl3 = SocketImpl.this;
                                        if (!zIsRequestedConnection) {
                                            if (Central.this.mSocketMaps.notifyDetected(SocketImpl.this.mBluetoothDevice, SocketImpl.this.mPeerInfo)) {
                                                SocketImpl.this.close();
                                                return;
                                            } else {
                                                Logger.m967d(Central.TAG, "Unknown error.");
                                                SocketImpl.this.abort();
                                                return;
                                            }
                                        }
                                        if (!Central.this.mSocketMaps.notifyConnected(Socket.this)) {
                                            SocketImpl.this.abort();
                                            return;
                                        }
                                        Logger.m967d(Central.TAG, "Connected peripheral. (device = " + SocketImpl.this.mBluetoothDevice.toString() + ", uuid = " + SocketImpl.this.mPeerInfo.getUuid() + ", id = " + SocketImpl.this.mPeerInfo.getId() + ", attribute = " + SocketImpl.this.mPeerInfo.getAttribute().toString() + ")");
                                    }
                                }
                            }
                            SocketImpl.this.abort();
                            return;
                        }
                        if (!SocketImpl.this.mBluetoothGatt.requestMtu(512)) {
                            Logger.m968e(Central.TAG, "Failed to request mtu.");
                            if (SocketImpl.this.mPeerInfo == null) {
                                readCharacteristicPeripheralAdvertisement();
                            } else {
                                writeDescriptorDownlink();
                            }
                        }
                    }
                }
            }

            private SocketImpl(BluetoothDevice bluetoothDevice) {
                this.mObjectId = Central.mNextSocketImplObjectId.getAndIncrement();
                this.mSendQueue = new ConcurrentLinkedQueue();
                this.mRecvQueue = new ConcurrentLinkedQueue();
                this.mSendingUplink = new AtomicBoolean(false);
                this.mMtu = 20;
                this.mState = BluetoothLowEnergySocket.State.OPEN;
                this.mStartedConnection = false;
                this.mBluetoothGattCallback = new BluetoothGattCallbackImpl();
                if (bluetoothDevice == null) {
                    this.mState = BluetoothLowEnergySocket.State.CLOSED;
                }
                this.mBluetoothDevice = bluetoothDevice;
                this.mState = BluetoothLowEnergySocket.State.OPEN;
            }

            private SocketImpl(BluetoothDevice bluetoothDevice, BluetoothLowEnergySocket.PeerInfo peerInfo) {
                this.mObjectId = Central.mNextSocketImplObjectId.getAndIncrement();
                this.mSendQueue = new ConcurrentLinkedQueue();
                this.mRecvQueue = new ConcurrentLinkedQueue();
                this.mSendingUplink = new AtomicBoolean(false);
                this.mMtu = 20;
                this.mState = BluetoothLowEnergySocket.State.OPEN;
                this.mStartedConnection = false;
                this.mBluetoothGattCallback = new BluetoothGattCallbackImpl();
                if (bluetoothDevice == null || peerInfo == null) {
                    this.mState = BluetoothLowEnergySocket.State.CLOSED;
                }
                this.mBluetoothDevice = bluetoothDevice;
                this.mPeerInfo = peerInfo;
                this.mState = BluetoothLowEnergySocket.State.OPEN;
            }

            /* JADX INFO: Access modifiers changed from: private */
            public void internalAbort() {
                if (internalAbortWithoutWait()) {
                    try {
                        Thread.sleep(1500L);
                    } catch (InterruptedException unused) {
                        Thread.currentThread().interrupt();
                    }
                }
            }

            private synchronized boolean internalAbortWithoutWait() {
                boolean z;
                if (this.mBluetoothGatt != null) {
                    this.mBluetoothGatt.disconnect();
                    this.mBluetoothGatt.close();
                    z = true;
                } else {
                    z = false;
                }
                this.mState = BluetoothLowEnergySocket.State.CLOSED;
                return z;
            }

            /* JADX INFO: Access modifiers changed from: private */
            public void internalClose() {
                synchronized (this) {
                    if (this.mState == BluetoothLowEnergySocket.State.CLOSED) {
                        return;
                    }
                    if (this.mBluetoothGatt == null) {
                        internalAbortWithoutWait();
                        return;
                    }
                    if (!this.mStartedConnection) {
                        internalAbort();
                        return;
                    }
                    this.mBluetoothGatt.disconnect();
                    while (this.mState == BluetoothLowEnergySocket.State.CLOSING) {
                        try {
                            Thread.sleep(100L);
                        } catch (InterruptedException unused) {
                            Thread.currentThread().interrupt();
                            return;
                        }
                    }
                }
            }

            private boolean internalEquals(SocketImpl socketImpl) {
                BluetoothDevice bluetoothDevice = this.mBluetoothDevice;
                if (bluetoothDevice == null) {
                    if (socketImpl.mBluetoothDevice != null) {
                        return false;
                    }
                } else if (!bluetoothDevice.equals(socketImpl.mBluetoothDevice)) {
                    return false;
                }
                if (this.mBluetoothGatt == null) {
                    if (socketImpl.mBluetoothGatt != null) {
                        return false;
                    }
                } else if (!this.mBluetoothGatt.equals(socketImpl.mBluetoothGatt)) {
                    return false;
                }
                if (this.mUplinkCharacteristic == null) {
                    if (socketImpl.mUplinkCharacteristic != null) {
                        return false;
                    }
                } else if (!this.mUplinkCharacteristic.equals(socketImpl.mUplinkCharacteristic)) {
                    return false;
                }
                if (this.mDownlinkCharacteristic == null) {
                    if (socketImpl.mDownlinkCharacteristic != null) {
                        return false;
                    }
                } else if (!this.mDownlinkCharacteristic.equals(socketImpl.mDownlinkCharacteristic)) {
                    return false;
                }
                if (this.mPeerInfo == null) {
                    if (socketImpl.mPeerInfo != null) {
                        return false;
                    }
                } else if (!this.mPeerInfo.equals(socketImpl.mPeerInfo)) {
                    return false;
                }
                Queue<byte[]> queue = this.mSendQueue;
                if (queue == null) {
                    if (socketImpl.mSendQueue != null) {
                        return false;
                    }
                } else if (!queue.equals(socketImpl.mSendQueue)) {
                    return false;
                }
                Queue<byte[]> queue2 = this.mRecvQueue;
                if (queue2 == null) {
                    if (socketImpl.mRecvQueue != null) {
                        return false;
                    }
                } else if (!queue2.equals(socketImpl.mRecvQueue)) {
                    return false;
                }
                AtomicBoolean atomicBoolean = this.mSendingUplink;
                if (atomicBoolean == null) {
                    if (socketImpl.mSendingUplink != null) {
                        return false;
                    }
                } else if (!atomicBoolean.equals(socketImpl.mSendingUplink)) {
                    return false;
                }
                if (this.mMtu != socketImpl.mMtu) {
                    return false;
                }
                if (this.mState == null) {
                    if (socketImpl.mState != null) {
                        return false;
                    }
                } else if (!this.mState.equals(socketImpl.mState)) {
                    return false;
                }
                return this.mStartedConnection == socketImpl.mStartedConnection;
            }

            /* JADX INFO: Access modifiers changed from: private */
            public void internalScan() {
                synchronized (this) {
                    if (this.mBluetoothGatt != null) {
                        Logger.m968e(Central.TAG, "Unknown error.");
                        return;
                    }
                    if (this.mState != BluetoothLowEnergySocket.State.CONNECTING) {
                        return;
                    }
                    if (this.mPeerInfo != null) {
                        abort();
                        return;
                    }
                    this.mBluetoothGatt = this.mBluetoothDevice.connectGatt(Central.this.mContext, false, this.mBluetoothGattCallback);
                    if (this.mBluetoothGatt == null) {
                        abort();
                        return;
                    }
                    try {
                        ElapsedTime elapsedTime = new ElapsedTime();
                        while (this.mState == BluetoothLowEnergySocket.State.CONNECTING) {
                            if (elapsedTime.get() >= 5000) {
                                close();
                                return;
                            }
                            Thread.sleep(100L);
                        }
                    } catch (InterruptedException unused) {
                        Thread.currentThread().interrupt();
                    }
                }
            }

            /* JADX INFO: Access modifiers changed from: private */
            public synchronized void requestSend() {
                byte[] bArrPoll;
                if (this.mUplinkCharacteristic == null) {
                    abort();
                    return;
                }
                synchronized (this.mSendQueue) {
                    if (this.mSendingUplink.compareAndSet(false, true)) {
                        try {
                            bArrPoll = this.mSendQueue.poll();
                        } catch (Throwable unused) {
                            this.mSendingUplink.set(false);
                        }
                        if (bArrPoll == null) {
                            throw new Exception();
                        }
                        if (!this.mUplinkCharacteristic.setValue(bArrPoll)) {
                            abort();
                            throw new Exception();
                        }
                        this.mUplinkCharacteristic.setWriteType(1);
                        if (this.mBluetoothGatt.writeCharacteristic(this.mUplinkCharacteristic)) {
                            return;
                        }
                        abort();
                        throw new Exception();
                    }
                }
            }

            protected synchronized void abort() {
                if (this.mState == BluetoothLowEnergySocket.State.CLOSED) {
                    return;
                }
                if (this.mBluetoothGatt == null) {
                    internalAbortWithoutWait();
                    return;
                }
                this.mState = BluetoothLowEnergySocket.State.CLOSING;
                try {
                    if (Central.this.mOperationQueue.offer(new PriorityQueueFifoEntry(2, new Runnable() { // from class: jp.konami.peerlink.ble.Central.Socket.SocketImpl.3
                        @Override // java.lang.Runnable
                        public void run() {
                            SocketImpl.this.internalAbort();
                        }
                    }))) {
                        return;
                    }
                    internalAbortWithoutWait();
                } catch (Exception unused) {
                    internalAbortWithoutWait();
                }
            }

            public synchronized void close() {
                if (this.mState != BluetoothLowEnergySocket.State.CLOSING && this.mState != BluetoothLowEnergySocket.State.CLOSED) {
                    if (this.mBluetoothGatt == null) {
                        internalAbortWithoutWait();
                        return;
                    }
                    this.mState = BluetoothLowEnergySocket.State.CLOSING;
                    try {
                        if (Central.this.mOperationQueue.offer(new PriorityQueueFifoEntry(1, new Runnable() { // from class: jp.konami.peerlink.ble.Central.Socket.SocketImpl.2
                            @Override // java.lang.Runnable
                            public void run() {
                                SocketImpl.this.internalClose();
                            }
                        }))) {
                            return;
                        }
                        internalAbortWithoutWait();
                    } catch (Exception unused) {
                        internalAbortWithoutWait();
                    }
                }
            }

            public synchronized boolean connect() {
                if (this.mState == BluetoothLowEnergySocket.State.OPEN && this.mPeerInfo != null) {
                    this.mState = BluetoothLowEnergySocket.State.CONNECTING;
                    if (Central.this.mSocketMaps.requestConnection(Socket.this)) {
                        return true;
                    }
                    this.mState = BluetoothLowEnergySocket.State.OPEN;
                    return false;
                }
                return false;
            }

            public void destruct() {
                abort();
            }

            public boolean equals(Object obj) {
                boolean zInternalEquals;
                boolean zInternalEquals2;
                if (this == obj) {
                    return true;
                }
                if (obj == null) {
                    return false;
                }
                if (!(obj instanceof SocketImpl)) {
                    return super.equals(obj);
                }
                SocketImpl socketImpl = (SocketImpl) obj;
                int iIdentityHashCode = System.identityHashCode(this);
                int iIdentityHashCode2 = System.identityHashCode(socketImpl);
                if (iIdentityHashCode > iIdentityHashCode2 || (iIdentityHashCode == iIdentityHashCode2 && this.mObjectId > socketImpl.mObjectId)) {
                    synchronized (this) {
                        synchronized (socketImpl) {
                            zInternalEquals = internalEquals(socketImpl);
                        }
                    }
                    return zInternalEquals;
                }
                if (iIdentityHashCode >= iIdentityHashCode2 && (iIdentityHashCode != iIdentityHashCode2 || this.mObjectId >= socketImpl.mObjectId)) {
                    return false;
                }
                synchronized (socketImpl) {
                    synchronized (this) {
                        zInternalEquals2 = internalEquals(socketImpl);
                    }
                }
                return zInternalEquals2;
            }

            public BluetoothLowEnergySocket.PeerInfo getPeerInfo() {
                return this.mPeerInfo;
            }

            public BluetoothLowEnergySocket.State getState() {
                return this.mState;
            }

            public int hashCode() {
                BluetoothGatt bluetoothGatt = this.mBluetoothGatt;
                BluetoothGattCharacteristic bluetoothGattCharacteristic = this.mUplinkCharacteristic;
                BluetoothGattCharacteristic bluetoothGattCharacteristic2 = this.mDownlinkCharacteristic;
                BluetoothLowEnergySocket.PeerInfo peerInfo = this.mPeerInfo;
                Queue<byte[]> queue = this.mSendQueue;
                Queue<byte[]> queue2 = this.mRecvQueue;
                AtomicBoolean atomicBoolean = this.mSendingUplink;
                int i = this.mMtu;
                BluetoothLowEnergySocket.State state = this.mState;
                boolean z = this.mStartedConnection;
                BluetoothDevice bluetoothDevice = this.mBluetoothDevice;
                return (bluetoothDevice == null ? 0 : bluetoothDevice.hashCode()) + (bluetoothGatt == null ? 0 : bluetoothGatt.hashCode()) + (bluetoothGattCharacteristic == null ? 0 : bluetoothGattCharacteristic.hashCode()) + (bluetoothGattCharacteristic2 == null ? 0 : bluetoothGattCharacteristic2.hashCode()) + (peerInfo == null ? 0 : peerInfo.hashCode()) + (queue == null ? 0 : queue.hashCode()) + (queue2 == null ? 0 : queue2.hashCode()) + (atomicBoolean == null ? 0 : atomicBoolean.hashCode()) + i + (state != null ? state.hashCode() : 0) + (z ? 1 : 0);
            }

            public synchronized byte[] recv() {
                if (this.mState != BluetoothLowEnergySocket.State.ESTABLISHED && this.mState != BluetoothLowEnergySocket.State.CLOSING) {
                    return null;
                }
                return this.mRecvQueue.poll();
            }

            public synchronized boolean scan() {
                if (this.mState == BluetoothLowEnergySocket.State.OPEN && this.mPeerInfo == null) {
                    this.mState = BluetoothLowEnergySocket.State.CONNECTING;
                    try {
                        if (Central.this.mOperationQueue.offer(new PriorityQueueFifoEntry(0, new Runnable() { // from class: jp.konami.peerlink.ble.Central.Socket.SocketImpl.1
                            @Override // java.lang.Runnable
                            public void run() {
                                SocketImpl.this.internalScan();
                            }
                        }))) {
                            return true;
                        }
                        this.mState = BluetoothLowEnergySocket.State.OPEN;
                        return false;
                    } catch (Exception unused) {
                        this.mState = BluetoothLowEnergySocket.State.OPEN;
                        return false;
                    }
                }
                return false;
            }

            public synchronized boolean send(byte[] bArr) {
                if (this.mState != BluetoothLowEnergySocket.State.ESTABLISHED) {
                    return false;
                }
                if (bArr.length != 0 && bArr.length <= this.mMtu) {
                    synchronized (this.mSendQueue) {
                        if (this.mSendQueue.size() >= 100) {
                            return false;
                        }
                        if (!this.mSendQueue.offer(bArr)) {
                            return false;
                        }
                        requestSend();
                        return this.mState == BluetoothLowEnergySocket.State.ESTABLISHED;
                    }
                }
                return false;
            }
        }

        private Socket(BluetoothDevice bluetoothDevice) {
            this.mObjectId = Central.mNextSocketObjectId.getAndIncrement();
            this.mSocketImpl = new SocketImpl(bluetoothDevice);
        }

        private Socket(BluetoothDevice bluetoothDevice, BluetoothLowEnergySocket.PeerInfo peerInfo) {
            this.mObjectId = Central.mNextSocketObjectId.getAndIncrement();
            this.mSocketImpl = new SocketImpl(bluetoothDevice, peerInfo);
        }

        private void internalSwap(Socket socket) {
            SocketImpl socketImpl = this.mSocketImpl;
            this.mSocketImpl = socket.mSocketImpl;
            socket.mSocketImpl = socketImpl;
        }

        @Override // jp.konami.peerlink.ble.BluetoothLowEnergySocket
        protected void abort() {
            this.mSocketImpl.abort();
        }

        @Override // jp.konami.peerlink.ble.BluetoothLowEnergySocket, java.io.Closeable, java.lang.AutoCloseable
        public void close() {
            this.mSocketImpl.close();
        }

        @Override // jp.konami.peerlink.ble.BluetoothLowEnergySocket
        public boolean connect() {
            return this.mSocketImpl.connect();
        }

        @Override // jp.konami.peerlink.ble.BluetoothLowEnergySocket
        public void destruct() {
            this.mSocketImpl.destruct();
        }

        public boolean equals(Object obj) {
            if (this == obj) {
                return true;
            }
            if (obj == null) {
                return false;
            }
            if (!(obj instanceof Socket)) {
                return super.equals(obj);
            }
            SocketImpl socketImpl = this.mSocketImpl;
            SocketImpl socketImpl2 = ((Socket) obj).mSocketImpl;
            return socketImpl == null ? socketImpl2 == null : socketImpl.equals(socketImpl2);
        }

        @Override // jp.konami.peerlink.ble.BluetoothLowEnergySocket
        public BluetoothLowEnergySocket.PeerInfo getPeerInfo() {
            return this.mSocketImpl.getPeerInfo();
        }

        @Override // jp.konami.peerlink.ble.BluetoothLowEnergySocket
        public BluetoothLowEnergySocket.State getState() {
            return this.mSocketImpl.getState();
        }

        public int hashCode() {
            SocketImpl socketImpl = this.mSocketImpl;
            if (socketImpl == null) {
                return 0;
            }
            return socketImpl.hashCode();
        }

        @Override // jp.konami.peerlink.ble.BluetoothLowEnergySocket
        public byte[] recv() {
            return this.mSocketImpl.recv();
        }

        public boolean scan() {
            return this.mSocketImpl.scan();
        }

        @Override // jp.konami.peerlink.ble.BluetoothLowEnergySocket
        public boolean send(byte[] bArr) {
            return this.mSocketImpl.send(bArr);
        }

        public void swap(Socket socket) {
            if (this == socket || socket == null) {
                return;
            }
            int iIdentityHashCode = System.identityHashCode(this);
            int iIdentityHashCode2 = System.identityHashCode(socket);
            if (iIdentityHashCode > iIdentityHashCode2 || (iIdentityHashCode == iIdentityHashCode2 && this.mObjectId > socket.mObjectId)) {
                synchronized (this) {
                    synchronized (socket) {
                        internalSwap(socket);
                    }
                }
            } else if (iIdentityHashCode < iIdentityHashCode2 || (iIdentityHashCode == iIdentityHashCode2 && this.mObjectId < socket.mObjectId)) {
                synchronized (socket) {
                    synchronized (this) {
                        internalSwap(socket);
                    }
                }
            }
        }
    }

    private class SocketMaps {
        private final ConcurrentMap<UUID, Socket> mConnectionMap;
        private final ConcurrentMap<UUID, DataWithTimeLimit<Socket>> mDetectedMap;
        private final ConcurrentMap<UUID, DataWithTimeLimit<Socket>> mRequestedConnectionMap;
        private final ConcurrentMap<BluetoothDevice, DataWithTimeLimit<Socket>> mScanningMap;

        private class DataWithTimeLimit<T> {
            private final T mData;
            private final ElapsedTime mElapsedTime;
            private final long mTimeLimit;
            private int mTimes;
            private final int mTimesLimit;

            public DataWithTimeLimit(long j, int i, T t) {
                this.mElapsedTime = j <= 0 ? null : new ElapsedTime();
                this.mTimeLimit = j;
                this.mTimesLimit = i;
                this.mData = t;
            }

            public DataWithTimeLimit(SocketMaps socketMaps, long j, T t) {
                this(j, 0, t);
            }

            public T getData() {
                return this.mData;
            }

            public void incrementTimes() {
                this.mTimes++;
            }

            public boolean isExpired() {
                int i = this.mTimesLimit;
                if (i > 0 && i <= this.mTimes) {
                    return true;
                }
                ElapsedTime elapsedTime = this.mElapsedTime;
                return elapsedTime != null && elapsedTime.get() >= this.mTimeLimit;
            }
        }

        private SocketMaps() {
            this.mScanningMap = new ConcurrentHashMap();
            this.mDetectedMap = new ConcurrentHashMap();
            this.mRequestedConnectionMap = new ConcurrentHashMap();
            this.mConnectionMap = new ConcurrentHashMap();
        }

        private void cleanup() {
            Socket data;
            Socket data2;
            Socket data3;
            Iterator<Map.Entry<BluetoothDevice, DataWithTimeLimit<Socket>>> it = this.mScanningMap.entrySet().iterator();
            while (it.hasNext()) {
                DataWithTimeLimit<Socket> value = it.next().getValue();
                if (!isScanningActivated(value)) {
                    it.remove();
                    if (value != null && (data3 = value.getData()) != null) {
                        data3.abort();
                    }
                }
            }
            Iterator<Map.Entry<UUID, DataWithTimeLimit<Socket>>> it2 = this.mDetectedMap.entrySet().iterator();
            while (it2.hasNext()) {
                DataWithTimeLimit<Socket> value2 = it2.next().getValue();
                if (!isDetectedActivated(value2)) {
                    it2.remove();
                    if (value2 != null && (data2 = value2.getData()) != null) {
                        data2.abort();
                    }
                }
            }
            Iterator<Map.Entry<UUID, DataWithTimeLimit<Socket>>> it3 = this.mRequestedConnectionMap.entrySet().iterator();
            while (it3.hasNext()) {
                DataWithTimeLimit<Socket> value3 = it3.next().getValue();
                if (!isRequestedConnectionActivated(value3)) {
                    it3.remove();
                    if (value3 != null && (data = value3.getData()) != null) {
                        data.abort();
                    }
                }
            }
            Iterator<Map.Entry<UUID, Socket>> it4 = this.mConnectionMap.entrySet().iterator();
            while (it4.hasNext()) {
                Socket value4 = it4.next().getValue();
                if (!isConnectionActivated(value4)) {
                    it4.remove();
                    if (value4 != null) {
                        value4.abort();
                    }
                }
            }
        }

        private Socket getConnectionIfActivated(UUID uuid) {
            Socket socket = this.mConnectionMap.get(uuid);
            if (isConnectionActivated(socket)) {
                return socket;
            }
            return null;
        }

        private DataWithTimeLimit<Socket> getDetectedIfActivated(UUID uuid) {
            DataWithTimeLimit<Socket> dataWithTimeLimit = this.mDetectedMap.get(uuid);
            if (isDetectedActivated(dataWithTimeLimit)) {
                return dataWithTimeLimit;
            }
            return null;
        }

        private DataWithTimeLimit<Socket> getRequestedConnectionIfActivated(UUID uuid) {
            DataWithTimeLimit<Socket> dataWithTimeLimit = this.mRequestedConnectionMap.get(uuid);
            if (isRequestedConnectionActivated(dataWithTimeLimit)) {
                return dataWithTimeLimit;
            }
            return null;
        }

        private DataWithTimeLimit<Socket> getScanningIfActivated(BluetoothDevice bluetoothDevice) {
            DataWithTimeLimit<Socket> dataWithTimeLimit = this.mScanningMap.get(bluetoothDevice);
            if (isScanningActivated(dataWithTimeLimit)) {
                return dataWithTimeLimit;
            }
            return null;
        }

        private boolean isConnectionActivated(Socket socket) {
            if (socket == null) {
                return false;
            }
            BluetoothLowEnergySocket.State state = socket.getState();
            return state == BluetoothLowEnergySocket.State.CONNECTING || state == BluetoothLowEnergySocket.State.ESTABLISHED || state == BluetoothLowEnergySocket.State.CLOSING;
        }

        private boolean isDetectedActivated(DataWithTimeLimit<Socket> dataWithTimeLimit) {
            Socket data;
            if (dataWithTimeLimit == null || (data = dataWithTimeLimit.getData()) == null) {
                return false;
            }
            BluetoothLowEnergySocket.State state = data.getState();
            if (state != BluetoothLowEnergySocket.State.CONNECTING) {
                return state == BluetoothLowEnergySocket.State.OPEN && !dataWithTimeLimit.isExpired();
            }
            return true;
        }

        private boolean isRequestedConnectionActivated(DataWithTimeLimit<Socket> dataWithTimeLimit) {
            Socket data;
            if (dataWithTimeLimit == null || (data = dataWithTimeLimit.getData()) == null) {
                return false;
            }
            BluetoothLowEnergySocket.State state = data.getState();
            if (state != BluetoothLowEnergySocket.State.ESTABLISHED) {
                return state == BluetoothLowEnergySocket.State.CONNECTING && !dataWithTimeLimit.isExpired();
            }
            return true;
        }

        private boolean isScanningActivated(DataWithTimeLimit<Socket> dataWithTimeLimit) {
            Socket data;
            return (dataWithTimeLimit == null || (data = dataWithTimeLimit.getData()) == null || data.getState() != BluetoothLowEnergySocket.State.CONNECTING || dataWithTimeLimit.isExpired()) ? false : true;
        }

        public void clearDetected() {
            this.mDetectedMap.clear();
        }

        public List<BluetoothLowEnergySocket> getDetectedSocketList() {
            Socket data;
            update();
            if (this.mDetectedMap.isEmpty()) {
                return null;
            }
            ArrayList arrayList = new ArrayList();
            for (DataWithTimeLimit<Socket> dataWithTimeLimit : this.mDetectedMap.values()) {
                if (isDetectedActivated(dataWithTimeLimit) && (data = dataWithTimeLimit.getData()) != null) {
                    arrayList.add(data);
                }
            }
            if (arrayList.isEmpty()) {
                return null;
            }
            return arrayList;
        }

        public BluetoothLowEnergySocket.PeerInfo getPeerInfoFromDetected(UUID uuid) {
            Socket data;
            DataWithTimeLimit<Socket> detectedIfActivated = getDetectedIfActivated(uuid);
            if (detectedIfActivated == null || (data = detectedIfActivated.getData()) == null) {
                return null;
            }
            return data.getPeerInfo();
        }

        public boolean isRequestedConnection(UUID uuid) {
            return getRequestedConnectionIfActivated(uuid) != null;
        }

        public boolean isScanning(BluetoothDevice bluetoothDevice) {
            return getScanningIfActivated(bluetoothDevice) != null;
        }

        public boolean notifyConnected(Socket socket) {
            BluetoothLowEnergySocket.PeerInfo peerInfo = socket.getPeerInfo();
            if (peerInfo == null) {
                return false;
            }
            UUID uuid = peerInfo.getUuid();
            synchronized (this) {
                DataWithTimeLimit<Socket> requestedConnectionIfActivated = getRequestedConnectionIfActivated(uuid);
                if (requestedConnectionIfActivated == null) {
                    return false;
                }
                Socket data = requestedConnectionIfActivated.getData();
                if (data == null) {
                    return false;
                }
                if (socket.mSocketImpl != null && this.mScanningMap.remove(socket.mSocketImpl.mBluetoothDevice) != null) {
                    if (this.mRequestedConnectionMap.remove(uuid) == null) {
                        return false;
                    }
                    data.swap(socket);
                    return this.mConnectionMap.putIfAbsent(uuid, data) == null;
                }
                return false;
            }
        }

        public synchronized boolean notifyDetected(BluetoothDevice bluetoothDevice, BluetoothLowEnergySocket.PeerInfo peerInfo) throws Throwable {
            try {
                try {
                    if (!isScanning(bluetoothDevice)) {
                        return false;
                    }
                    if (this.mScanningMap.remove(bluetoothDevice) == null) {
                        return false;
                    }
                    Socket socket = new Socket(bluetoothDevice, peerInfo);
                    if (socket.getState() != BluetoothLowEnergySocket.State.OPEN) {
                        return false;
                    }
                    this.mDetectedMap.put(peerInfo.getUuid(), new DataWithTimeLimit<>(Constants.WATCHDOG_WAKE_TIMER, 3, socket));
                    return true;
                } catch (Throwable th) {
                    th = th;
                }
            } catch (Throwable th2) {
                th = th2;
            }
            throw th;
        }

        public boolean notifyStartedScan(BluetoothDevice bluetoothDevice, Socket socket) {
            return this.mScanningMap.putIfAbsent(bluetoothDevice, new DataWithTimeLimit<>(this, WorkRequest.DEFAULT_BACKOFF_DELAY_MILLIS, socket)) == null;
        }

        public boolean requestConnection(Socket socket) {
            BluetoothLowEnergySocket.PeerInfo peerInfo = socket.getPeerInfo();
            if (peerInfo == null) {
                return false;
            }
            UUID uuid = peerInfo.getUuid();
            synchronized (this) {
                if (getRequestedConnectionIfActivated(uuid) != null) {
                    return false;
                }
                if (getConnectionIfActivated(uuid) != null) {
                    return false;
                }
                if (getDetectedIfActivated(uuid) == null) {
                    return false;
                }
                if (this.mDetectedMap.remove(uuid) == null) {
                    return false;
                }
                return this.mRequestedConnectionMap.putIfAbsent(uuid, new DataWithTimeLimit<>(this, Constants.WATCHDOG_WAKE_TIMER, socket)) == null;
            }
        }

        public void update() {
            cleanup();
        }

        public void updateDetectedTimer() {
            Iterator<Map.Entry<UUID, DataWithTimeLimit<Socket>>> it = this.mDetectedMap.entrySet().iterator();
            while (it.hasNext()) {
                try {
                    it.next().getValue().incrementTimes();
                } catch (Exception e) {
                    e.printStackTrace();
                }
            }
        }
    }

    public enum State {
        UNSUPPORTED,
        ACTIVATING,
        ACTIVATED,
        INACTIVATING,
        INACTIVATED
    }

    public Central(Config config, Context context) throws IllegalArgumentException {
        Context context2;
        this.mState = State.UNSUPPORTED;
        Thread thread = new Thread(new Runnable() { // from class: jp.konami.peerlink.ble.Central.1
            @Override // java.lang.Runnable
            public void run() {
                ElapsedTime elapsedTime = new ElapsedTime();
                while (true) {
                    try {
                        if (Central.this.mScanTime != null) {
                            long j = 2000 - Central.this.mScanTime.get();
                            if (j > 0) {
                                Thread.sleep(j);
                            }
                        }
                        Central.this.internalStopScan();
                        elapsedTime.reset();
                        while (true) {
                            long j2 = elapsedTime.get();
                            PriorityQueueFifoEntry priorityQueueFifoEntry = (PriorityQueueFifoEntry) Central.this.mOperationQueue.poll(j2 >= 5000 ? 0L : 5000 - j2, TimeUnit.MILLISECONDS);
                            if (priorityQueueFifoEntry == null) {
                                break;
                            } else {
                                ((Runnable) priorityQueueFifoEntry.getData()).run();
                            }
                        }
                        if (Central.this.mScanState == ScanState.ACTIVATING || Central.this.mScanState == ScanState.ACTIVATED) {
                            Central.this.mSocketMaps.updateDetectedTimer();
                            Central.this.internalStartScan();
                        }
                        Central.this.mSocketMaps.update();
                    } catch (InterruptedException e) {
                        e.printStackTrace();
                        return;
                    } catch (Exception e2) {
                        e2.printStackTrace();
                    }
                }
            }
        });
        this.mOperationThread = thread;
        this.mScanCallback = new ScanCallback() { // from class: jp.konami.peerlink.ble.Central.2
            @Override // android.bluetooth.le.ScanCallback
            public void onBatchScanResults(List<ScanResult> list) {
                Iterator<ScanResult> it = list.iterator();
                while (it.hasNext()) {
                    Logger.m967d(Central.TAG, "BatchScanResults: result = " + it.next().toString());
                }
            }

            @Override // android.bluetooth.le.ScanCallback
            public void onScanFailed(int i) {
                Logger.m968e(Central.TAG, "Failed to start scan. (errorCode = " + i + ")");
                Central.this.mScanState = ScanState.INACTIVATED;
            }

            @Override // android.bluetooth.le.ScanCallback
            public void onScanResult(int i, ScanResult scanResult) {
                Logger.m967d(Central.TAG, "ScanResult: callbackType = " + i + ", result = " + scanResult.toString());
                BluetoothDevice device = scanResult.getDevice();
                if (Central.this.mSocketMaps.isScanning(device)) {
                    return;
                }
                Iterator<ParcelUuid> it = scanResult.getScanRecord().getServiceUuids().iterator();
                while (it.hasNext()) {
                    if (it.next().equals(ParcelUuid.fromString(Central.this.mConfig.getServiceUuid()))) {
                        Socket socket = new Socket(device);
                        if (socket.scan()) {
                            if (Central.this.mSocketMaps.notifyStartedScan(device, socket)) {
                                Logger.m967d(Central.TAG, "Scanning for device. (device = " + device.toString() + ")");
                                return;
                            } else {
                                Logger.m967d(Central.TAG, "Unknown error.");
                                socket.abort();
                                return;
                            }
                        }
                        return;
                    }
                }
            }
        };
        this.mConfig = config;
        this.mContext = context;
        if (!config.isValid() || (context2 = this.mContext) == null) {
            Logger.m968e(TAG, "Invalid argument.");
            throw new IllegalArgumentException("Invalid argument.");
        }
        if (!context2.getPackageManager().hasSystemFeature("android.hardware.bluetooth_le")) {
            this.mState = State.UNSUPPORTED;
            return;
        }
        BluetoothManager bluetoothManager = (BluetoothManager) this.mContext.getSystemService("bluetooth");
        this.mBluetoothManager = bluetoothManager;
        if (bluetoothManager == null) {
            this.mState = State.UNSUPPORTED;
            return;
        }
        BluetoothAdapter adapter = bluetoothManager.getAdapter();
        this.mBluetoothAdapter = adapter;
        if (adapter == null || !adapter.isEnabled()) {
            this.mState = State.INACTIVATED;
            return;
        }
        BluetoothLeScanner bluetoothLeScanner = this.mBluetoothAdapter.getBluetoothLeScanner();
        this.mBluetoothLeScanner = bluetoothLeScanner;
        if (bluetoothLeScanner == null) {
            this.mState = State.INACTIVATED;
        } else {
            thread.start();
            this.mState = State.ACTIVATED;
        }
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void internalStartScan() {
        if (this.mScanTime != null) {
            return;
        }
        this.mBluetoothLeScanner.startScan(Arrays.asList(new ScanFilter.Builder().setServiceUuid(ParcelUuid.fromString(this.mConfig.getServiceUuid())).build()), new ScanSettings.Builder().setScanMode(2).build(), this.mScanCallback);
        this.mScanTime = new ElapsedTime();
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void internalStopScan() {
        if (this.mScanTime == null) {
            return;
        }
        this.mBluetoothLeScanner.stopScan(this.mScanCallback);
        this.mScanTime = null;
    }

    public void destruct() {
        this.mOperationThread.interrupt();
        try {
            this.mOperationThread.join();
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
        if (!stopScan()) {
            this.mScanState = ScanState.INACTIVATED;
        }
        this.mState = State.UNSUPPORTED;
    }

    public List<BluetoothLowEnergySocket> getDetectedSocketList() {
        return this.mSocketMaps.getDetectedSocketList();
    }

    public ScanState getScanState() {
        return this.mScanState;
    }

    public State getState() {
        return this.mState;
    }

    public boolean startScan() {
        if (this.mBluetoothLeScanner == null || this.mState != State.ACTIVATED || this.mScanState != ScanState.INACTIVATED) {
            return false;
        }
        this.mSocketMaps.clearDetected();
        this.mScanState = ScanState.ACTIVATED;
        return true;
    }

    public boolean stopScan() {
        if (this.mBluetoothLeScanner == null || this.mState != State.ACTIVATED || this.mScanState != ScanState.ACTIVATED) {
            return false;
        }
        internalStopScan();
        this.mSocketMaps.clearDetected();
        this.mScanState = ScanState.INACTIVATED;
        return true;
    }
}

===== managed-work/jadx/sources/jp/konami/peerlink/ble/Peripheral.java =====
package jp.konami.peerlink.ble;

import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothDevice;
import android.bluetooth.BluetoothGattCharacteristic;
import android.bluetooth.BluetoothGattDescriptor;
import android.bluetooth.BluetoothGattServer;
import android.bluetooth.BluetoothGattServerCallback;
import android.bluetooth.BluetoothGattService;
import android.bluetooth.BluetoothManager;
import android.bluetooth.le.AdvertiseCallback;
import android.bluetooth.le.AdvertiseData;
import android.bluetooth.le.AdvertiseSettings;
import android.bluetooth.le.BluetoothLeAdvertiser;
import android.content.Context;
import android.os.ParcelUuid;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Queue;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.atomic.AtomicBoolean;
import jp.konami.Logger;
import jp.konami.peerlink.ble.BluetoothLowEnergySocket;

/* JADX INFO: loaded from: classes3.dex */
public class Peripheral {
    private static final String CONFIG_UUID = "00002902-0000-1000-8000-00805F9B34FB";
    private static final int MAX_CHARACTERISTIC_VALUE_LENGTH = 512;
    private static final String TAG = "Peripheral";
    private final AdvertiseCallback mAdvertiseCallback;
    private AdvertiseState mAdvertiseState;
    private BluetoothAdapter mBluetoothAdapter;
    private BluetoothGattServer mBluetoothGattServer;
    private final BluetoothGattServerCallback mBluetoothGattServerCallback;
    private BluetoothLeAdvertiser mBluetoothLeAdvertiser;
    private BluetoothManager mBluetoothManager;
    private Config mConfig;
    private Context mContext;
    private Sender mSender;
    private final Map<BluetoothDevice, Socket> mSocketMap;
    private State mState;
    private final UUID mUuid;

    public enum AdvertiseState {
        ACTIVATING,
        ACTIVATED,
        INACTIVATING,
        INACTIVATED
    }

    public static class Config {
        private Map mAttribute;
        private String mCentralAdvertisementUuid;
        private String mDownlinkUuid;
        private String mId;
        private String mPeripheralAdvertisementUuid;
        private String mServiceId;
        private String mServiceUuid;
        private String mUplinkUuid;

        /* JADX INFO: Access modifiers changed from: private */
        public boolean isValid() {
            String str;
            String str2;
            String str3;
            String str4;
            String str5;
            String str6;
            String str7 = this.mServiceId;
            return (str7 == null || str7.isEmpty() || (str = this.mId) == null || str.isEmpty() || (str2 = this.mServiceUuid) == null || str2.isEmpty() || (str3 = this.mPeripheralAdvertisementUuid) == null || str3.isEmpty() || (str4 = this.mCentralAdvertisementUuid) == null || str4.isEmpty() || (str5 = this.mUplinkUuid) == null || str5.isEmpty() || (str6 = this.mDownlinkUuid) == null || str6.isEmpty()) ? false : true;
        }

        public Map<String, String> getAttribute() {
            return this.mAttribute;
        }

        public String getCentralAdvertisementUuid() {
            return this.mCentralAdvertisementUuid;
        }

        public String getDownlinkUuid() {
            return this.mDownlinkUuid;
        }

        public String getId() {
            return this.mId;
        }

        public String getPeripheralAdvertisementUuid() {
            return this.mPeripheralAdvertisementUuid;
        }

        public String getServiceId() {
            return this.mServiceId;
        }

        public String getServiceUuid() {
            return this.mServiceUuid;
        }

        public String getUplinkUuid() {
            return this.mUplinkUuid;
        }

        public void setAttribute(String str, String str2) {
            if (this.mAttribute == null) {
                this.mAttribute = new HashMap();
            }
            this.mAttribute.put(str, str2);
        }

        public void setCentralAdvertisementUuid(String str) {
            this.mCentralAdvertisementUuid = str;
        }

        public void setDownlinkUuid(String str) {
            this.mDownlinkUuid = str;
        }

        public void setId(String str) {
            this.mId = str;
        }

        public void setPeripheralAdvertisementUuid(String str) {
            this.mPeripheralAdvertisementUuid = str;
        }

        public void setServiceId(String str) {
            this.mServiceId = str;
        }

        public void setServiceUuid(String str) {
            this.mServiceUuid = str;
        }

        public void setUplinkUuid(String str) {
            this.mUplinkUuid = str;
        }
    }

    private class Sender {
        private static final int MAX_SEND_QUEUE_SIZE = 500;
        private BluetoothGattCharacteristic mDownlinkCharacteristic;
        private Queue<SendData> mSendQueue = new ConcurrentLinkedQueue();
        private AtomicBoolean mSendingDownlink = new AtomicBoolean(false);

        private class SendData {
            private BluetoothDevice mBluetoothDevice;
            private byte[] mData;

            public SendData(BluetoothDevice bluetoothDevice, byte[] bArr) {
                this.mBluetoothDevice = bluetoothDevice;
                this.mData = bArr;
            }

            public BluetoothDevice getBluetoothDevice() {
                return this.mBluetoothDevice;
            }

            public byte[] getData() {
                return this.mData;
            }
        }

        public Sender(BluetoothGattCharacteristic bluetoothGattCharacteristic) {
            this.mDownlinkCharacteristic = bluetoothGattCharacteristic;
        }

        /* JADX INFO: Access modifiers changed from: private */
        public void onNotificationSent(BluetoothDevice bluetoothDevice, int i) {
            if (i != 0) {
                Peripheral.this.abort(bluetoothDevice);
            }
            this.mSendingDownlink.set(false);
            requestSend();
        }

        public boolean push(BluetoothDevice bluetoothDevice, byte[] bArr) {
            if (bluetoothDevice == null || bArr == null || bArr.length == 0) {
                return false;
            }
            synchronized (this.mSendQueue) {
                if (this.mSendQueue.size() >= 500) {
                    return false;
                }
                return this.mSendQueue.offer(new SendData(bluetoothDevice, bArr));
            }
        }

        public void requestSend() {
            SendData sendDataPoll;
            if (Peripheral.this.mBluetoothGattServer == null || this.mDownlinkCharacteristic == null) {
                return;
            }
            synchronized (this.mSendQueue) {
                if (this.mSendingDownlink.compareAndSet(false, true)) {
                    try {
                        sendDataPoll = this.mSendQueue.poll();
                    } catch (Throwable unused) {
                        this.mSendingDownlink.set(false);
                    }
                    if (sendDataPoll == null) {
                        throw new Exception();
                    }
                    BluetoothDevice bluetoothDevice = sendDataPoll.getBluetoothDevice();
                    if (bluetoothDevice == null) {
                        Peripheral.this.abort(bluetoothDevice);
                        throw new Exception();
                    }
                    byte[] data = sendDataPoll.getData();
                    if (data == null) {
                        Peripheral.this.abort(bluetoothDevice);
                        throw new Exception();
                    }
                    boolean value = this.mDownlinkCharacteristic.setValue(data);
                    Peripheral peripheral = Peripheral.this;
                    if (!value) {
                        peripheral.abort(bluetoothDevice);
                        throw new Exception();
                    }
                    if (peripheral.mBluetoothGattServer.notifyCharacteristicChanged(bluetoothDevice, this.mDownlinkCharacteristic, false)) {
                        return;
                    }
                    Peripheral.this.abort(bluetoothDevice);
                    throw new Exception();
                }
            }
        }
    }

    private class Socket extends BluetoothLowEnergySocket {
        private static final int MAX_RECV_QUEUE_SIZE = 1000;
        private BluetoothDevice mBluetoothDevice;
        private PreparedWriteBuffer mCentralAdvertisementPreparedWriteBuffer;
        private int mMtu;
        private BluetoothLowEnergySocket.PeerInfo mPeerInfo;
        private Queue<byte[]> mRecvQueue;
        private BluetoothLowEnergySocket.State mState;
        private PreparedWriteBuffer mUplinkPreparedWriteBuffer;

        private class PreparedWriteBuffer {
            private byte[] mBuffer;
            private int mDataLength;
            private int mRequestId;

            private PreparedWriteBuffer() {
                this.mRequestId = 0;
                this.mBuffer = new byte[512];
                this.mDataLength = 0;
            }

            /* JADX INFO: Access modifiers changed from: private */
            public boolean add(int i, int i2, byte[] bArr) {
                int length = bArr.length + i2;
                byte[] bArr2 = this.mBuffer;
                if (length > bArr2.length) {
                    return false;
                }
                if (this.mDataLength == 0) {
                    this.mRequestId = i;
                } else if (this.mRequestId != i) {
                    return false;
                }
                System.arraycopy(bArr, 0, bArr2, i2, bArr.length);
                this.mDataLength = Math.max(this.mDataLength, i2 + bArr.length);
                return true;
            }

            /* JADX INFO: Access modifiers changed from: private */
            public void clear() {
                this.mRequestId = 0;
                Arrays.fill(this.mBuffer, (byte) 0);
                this.mDataLength = 0;
            }

            /* JADX INFO: Access modifiers changed from: private */
            public byte[] get(int i) {
                int i2 = this.mDataLength;
                if (i2 == 0 || this.mRequestId != i) {
                    return null;
                }
                return Arrays.copyOfRange(this.mBuffer, 0, i2);
            }

            public boolean equals(Object obj) {
                if (obj == null) {
                    return false;
                }
                if (!(obj instanceof PreparedWriteBuffer)) {
                    return super.equals(obj);
                }
                PreparedWriteBuffer preparedWriteBuffer = (PreparedWriteBuffer) obj;
                return this.mRequestId == preparedWriteBuffer.mRequestId && Arrays.equals(this.mBuffer, preparedWriteBuffer.mBuffer) && this.mDataLength == preparedWriteBuffer.mDataLength;
            }

            public int hashCode() {
                return this.mRequestId + Arrays.hashCode(this.mBuffer) + this.mDataLength;
            }
        }

        private Socket(BluetoothDevice bluetoothDevice) {
            this.mCentralAdvertisementPreparedWriteBuffer = new PreparedWriteBuffer();
            this.mUplinkPreparedWriteBuffer = new PreparedWriteBuffer();
            this.mRecvQueue = new ConcurrentLinkedQueue();
            this.mMtu = 20;
            this.mState = BluetoothLowEnergySocket.State.OPEN;
            if (bluetoothDevice == null) {
                this.mState = BluetoothLowEnergySocket.State.CLOSED;
            }
            this.mBluetoothDevice = bluetoothDevice;
            this.mState = BluetoothLowEnergySocket.State.OPEN;
        }

        /* JADX INFO: Access modifiers changed from: private */
        public void onCharacteristicReadRequest(BluetoothDevice bluetoothDevice, int i, int i2, BluetoothGattCharacteristic bluetoothGattCharacteristic) {
            if (!bluetoothDevice.equals(this.mBluetoothDevice)) {
                Logger.m968e(Peripheral.TAG, "Unknown error.");
                abort();
            } else if (this.mState != BluetoothLowEnergySocket.State.OPEN) {
                if (!Peripheral.this.mBluetoothGattServer.sendResponse(bluetoothDevice, i, 257, i2, null)) {
                    Logger.m968e(Peripheral.TAG, "Unknown error.");
                }
                abort();
            } else {
                if (!bluetoothGattCharacteristic.getUuid().equals(UUID.fromString(Peripheral.this.mConfig.getPeripheralAdvertisementUuid())) || Peripheral.this.mBluetoothGattServer.sendResponse(bluetoothDevice, i, 0, i2, bluetoothGattCharacteristic.getValue())) {
                    return;
                }
                Logger.m968e(Peripheral.TAG, "Unknown error.");
                abort();
            }
        }

        /* JADX INFO: Access modifiers changed from: private */
        public void onCharacteristicWriteRequest(BluetoothDevice bluetoothDevice, int i, BluetoothGattCharacteristic bluetoothGattCharacteristic, boolean z, boolean z2, int i2, byte[] bArr) {
            BluetoothDevice bluetoothDevice2;
            int i3;
            int i4;
            int i5;
            int i6;
            if (!bluetoothDevice.equals(this.mBluetoothDevice)) {
                Logger.m968e(Peripheral.TAG, "Unknown error.");
                abort();
                return;
            }
            if (this.mState != BluetoothLowEnergySocket.State.OPEN) {
                bluetoothDevice2 = bluetoothDevice;
                i3 = i;
                i4 = i2;
                if ((this.mState == BluetoothLowEnergySocket.State.CONNECTING || this.mState == BluetoothLowEnergySocket.State.ESTABLISHED) && bluetoothGattCharacteristic.getUuid().equals(UUID.fromString(Peripheral.this.mConfig.getUplinkUuid()))) {
                    if (z2 && !Peripheral.this.mBluetoothGattServer.sendResponse(bluetoothDevice2, i3, 0, i4, null)) {
                        Logger.m968e(Peripheral.TAG, "Unknown error.");
                        abort();
                        return;
                    }
                    if (z) {
                        if (this.mUplinkPreparedWriteBuffer.add(i3, i4, bArr)) {
                            return;
                        }
                        Logger.m968e(Peripheral.TAG, "Unknown error.");
                        abort();
                        return;
                    }
                    synchronized (this.mRecvQueue) {
                        if (this.mRecvQueue.size() >= 1000) {
                            Logger.m968e(Peripheral.TAG, "Recv queue is full.");
                            abort();
                            return;
                        } else {
                            if (this.mRecvQueue.offer(bArr)) {
                                return;
                            }
                            Logger.m968e(Peripheral.TAG, "Failed to offer recv queue.");
                            abort();
                            return;
                        }
                    }
                }
            } else {
                if (bluetoothGattCharacteristic.getUuid().equals(UUID.fromString(Peripheral.this.mConfig.getCentralAdvertisementUuid()))) {
                    if (z2) {
                        i5 = i;
                        i6 = i2;
                        if (!Peripheral.this.mBluetoothGattServer.sendResponse(bluetoothDevice, i5, 0, i6, null)) {
                            Logger.m968e(Peripheral.TAG, "Unknown error.");
                            abort();
                            return;
                        }
                    } else {
                        i5 = i;
                        i6 = i2;
                    }
                    if (z) {
                        if (this.mCentralAdvertisementPreparedWriteBuffer.add(i5, i6, bArr)) {
                            return;
                        }
                        Logger.m968e(Peripheral.TAG, "Unknown error.");
                        abort();
                        return;
                    }
                    try {
                        AdvertisementHeader advertisementHeader = new AdvertisementHeader(bArr);
                        if (!advertisementHeader.getServiceId().equals(Peripheral.this.mConfig.getServiceId())) {
                            abort();
                            return;
                        } else {
                            this.mPeerInfo = new BluetoothLowEnergySocket.PeerInfo(advertisementHeader.getUuid(), advertisementHeader.getId(), advertisementHeader.getAttribute());
                            this.mState = BluetoothLowEnergySocket.State.CONNECTING;
                            return;
                        }
                    } catch (IllegalArgumentException e) {
                        Logger.m968e(Peripheral.TAG, "Failed to deserialize advertisement header.");
                        e.printStackTrace();
                        abort();
                        return;
                    }
                }
                bluetoothDevice2 = bluetoothDevice;
                i3 = i;
                i4 = i2;
            }
            if (!Peripheral.this.mBluetoothGattServer.sendResponse(bluetoothDevice2, i3, 257, i4, null)) {
                Logger.m968e(Peripheral.TAG, "Unknown error.");
            }
            abort();
        }

        /* JADX INFO: Access modifiers changed from: private */
        public void onDescriptorReadRequest(BluetoothDevice bluetoothDevice, int i, int i2, BluetoothGattDescriptor bluetoothGattDescriptor) {
            abort();
        }

        /* JADX INFO: Access modifiers changed from: private */
        public void onDescriptorWriteRequest(BluetoothDevice bluetoothDevice, int i, BluetoothGattDescriptor bluetoothGattDescriptor, boolean z, boolean z2, int i2, byte[] bArr) {
            if (!bluetoothDevice.equals(this.mBluetoothDevice)) {
                Logger.m968e(Peripheral.TAG, "Unknown error.");
                abort();
                return;
            }
            if (this.mState != BluetoothLowEnergySocket.State.OPEN) {
                abort();
                return;
            }
            if (!bluetoothGattDescriptor.getUuid().equals(UUID.fromString(Peripheral.CONFIG_UUID))) {
                abort();
            } else {
                if (!z2 || Peripheral.this.mBluetoothGattServer.sendResponse(bluetoothDevice, i, 0, i2, null)) {
                    return;
                }
                Logger.m968e(Peripheral.TAG, "Unknown error.");
                abort();
            }
        }

        /* JADX INFO: Access modifiers changed from: private */
        public void onExecuteWrite(BluetoothDevice bluetoothDevice, int i, boolean z) {
            if (!bluetoothDevice.equals(this.mBluetoothDevice)) {
                Logger.m968e(Peripheral.TAG, "Unknown error.");
                abort();
                return;
            }
            if (this.mState == BluetoothLowEnergySocket.State.OPEN) {
                if (z) {
                    byte[] bArr = this.mCentralAdvertisementPreparedWriteBuffer.get(i);
                    if (bArr == null) {
                        abort();
                        return;
                    }
                    try {
                        AdvertisementHeader advertisementHeader = new AdvertisementHeader(bArr);
                        if (!advertisementHeader.getServiceId().equals(Peripheral.this.mConfig.getServiceId())) {
                            abort();
                            return;
                        } else {
                            this.mPeerInfo = new BluetoothLowEnergySocket.PeerInfo(advertisementHeader.getUuid(), advertisementHeader.getId(), advertisementHeader.getAttribute());
                            this.mState = BluetoothLowEnergySocket.State.CONNECTING;
                        }
                    } catch (IllegalArgumentException e) {
                        Logger.m968e(Peripheral.TAG, "Failed to deserialize advertisement header.");
                        e.printStackTrace();
                        abort();
                        return;
                    }
                }
                this.mCentralAdvertisementPreparedWriteBuffer.clear();
                return;
            }
            if (this.mState == BluetoothLowEnergySocket.State.CONNECTING || this.mState == BluetoothLowEnergySocket.State.ESTABLISHED) {
                if (z) {
                    byte[] bArr2 = this.mUplinkPreparedWriteBuffer.get(i);
                    if (bArr2 == null) {
                        abort();
                        return;
                    }
                    synchronized (this.mRecvQueue) {
                        if (this.mRecvQueue.size() >= 1000) {
                            Logger.m968e(Peripheral.TAG, "Recv queue is full.");
                            abort();
                            return;
                        } else if (!this.mRecvQueue.offer(bArr2)) {
                            Logger.m968e(Peripheral.TAG, "Failed to offer recv queue.");
                            abort();
                            return;
                        }
                    }
                }
                this.mUplinkPreparedWriteBuffer.clear();
            }
        }

        /* JADX INFO: Access modifiers changed from: private */
        public void onMtuChanged(BluetoothDevice bluetoothDevice, int i) {
            if (bluetoothDevice.equals(this.mBluetoothDevice)) {
                Logger.m967d(Peripheral.TAG, "onMtuChanged: " + this.mMtu + " -> " + i);
                this.mMtu = i;
            } else {
                Logger.m968e(Peripheral.TAG, "Unknown error.");
                abort();
            }
        }

        @Override // jp.konami.peerlink.ble.BluetoothLowEnergySocket
        protected void abort() {
            if (Peripheral.this.mBluetoothGattServer != null && this.mBluetoothDevice != null) {
                Peripheral.this.mBluetoothGattServer.cancelConnection(this.mBluetoothDevice);
            }
            this.mState = BluetoothLowEnergySocket.State.CLOSED;
        }

        @Override // jp.konami.peerlink.ble.BluetoothLowEnergySocket
        public boolean accept() {
            if (this.mState != BluetoothLowEnergySocket.State.CONNECTING) {
                return false;
            }
            this.mState = BluetoothLowEnergySocket.State.ESTABLISHED;
            return true;
        }

        @Override // jp.konami.peerlink.ble.BluetoothLowEnergySocket, java.io.Closeable, java.lang.AutoCloseable
        public void close() {
            if (this.mState == BluetoothLowEnergySocket.State.CLOSING || this.mState == BluetoothLowEnergySocket.State.CLOSED) {
                return;
            }
            if (Peripheral.this.mBluetoothGattServer == null || this.mBluetoothDevice == null) {
                abort();
            } else {
                Peripheral.this.mBluetoothGattServer.cancelConnection(this.mBluetoothDevice);
                this.mState = BluetoothLowEnergySocket.State.CLOSING;
            }
        }

        @Override // jp.konami.peerlink.ble.BluetoothLowEnergySocket
        public void destruct() {
            abort();
        }

        public boolean equals(Object obj) {
            if (obj == null) {
                return false;
            }
            if (!(obj instanceof Socket)) {
                return super.equals(obj);
            }
            Socket socket = (Socket) obj;
            BluetoothDevice bluetoothDevice = this.mBluetoothDevice;
            if (bluetoothDevice != null ? bluetoothDevice.equals(socket.mBluetoothDevice) : socket.mBluetoothDevice == null) {
                BluetoothLowEnergySocket.PeerInfo peerInfo = this.mPeerInfo;
                if (peerInfo != null ? peerInfo.equals(socket.mPeerInfo) : socket.mPeerInfo == null) {
                    PreparedWriteBuffer preparedWriteBuffer = this.mCentralAdvertisementPreparedWriteBuffer;
                    if (preparedWriteBuffer != null ? preparedWriteBuffer.equals(socket.mCentralAdvertisementPreparedWriteBuffer) : socket.mCentralAdvertisementPreparedWriteBuffer == null) {
                        PreparedWriteBuffer preparedWriteBuffer2 = this.mUplinkPreparedWriteBuffer;
                        if (preparedWriteBuffer2 != null ? preparedWriteBuffer2.equals(socket.mUplinkPreparedWriteBuffer) : socket.mUplinkPreparedWriteBuffer == null) {
                            Queue<byte[]> queue = this.mRecvQueue;
                            if (queue != null ? queue.equals(socket.mRecvQueue) : socket.mRecvQueue == null) {
                                if (this.mMtu == socket.mMtu) {
                                    BluetoothLowEnergySocket.State state = this.mState;
                                    BluetoothLowEnergySocket.State state2 = socket.mState;
                                    if (state == null) {
                                        if (state2 == null) {
                                            return true;
                                        }
                                    } else if (state.equals(state2)) {
                                        return true;
                                    }
                                }
                            }
                        }
                    }
                }
            }
            return false;
        }

        @Override // jp.konami.peerlink.ble.BluetoothLowEnergySocket
        public BluetoothLowEnergySocket.PeerInfo getPeerInfo() {
            return this.mPeerInfo;
        }

        @Override // jp.konami.peerlink.ble.BluetoothLowEnergySocket
        public BluetoothLowEnergySocket.State getState() {
            return this.mState;
        }

        public int hashCode() {
            BluetoothDevice bluetoothDevice = this.mBluetoothDevice;
            int iHashCode = bluetoothDevice == null ? 0 : bluetoothDevice.hashCode();
            BluetoothLowEnergySocket.PeerInfo peerInfo = this.mPeerInfo;
            int iHashCode2 = iHashCode + (peerInfo == null ? 0 : peerInfo.hashCode());
            PreparedWriteBuffer preparedWriteBuffer = this.mCentralAdvertisementPreparedWriteBuffer;
            int iHashCode3 = iHashCode2 + (preparedWriteBuffer == null ? 0 : preparedWriteBuffer.hashCode());
            PreparedWriteBuffer preparedWriteBuffer2 = this.mUplinkPreparedWriteBuffer;
            int iHashCode4 = iHashCode3 + (preparedWriteBuffer2 == null ? 0 : preparedWriteBuffer2.hashCode());
            Queue<byte[]> queue = this.mRecvQueue;
            int iHashCode5 = iHashCode4 + (queue == null ? 0 : queue.hashCode()) + this.mMtu;
            BluetoothLowEnergySocket.State state = this.mState;
            return iHashCode5 + (state != null ? state.hashCode() : 0);
        }

        @Override // jp.konami.peerlink.ble.BluetoothLowEnergySocket
        public byte[] recv() {
            if (this.mState != BluetoothLowEnergySocket.State.ESTABLISHED) {
                return null;
            }
            return this.mRecvQueue.poll();
        }

        @Override // jp.konami.peerlink.ble.BluetoothLowEnergySocket
        public boolean send(byte[] bArr) {
            if (this.mState != BluetoothLowEnergySocket.State.ESTABLISHED || bArr.length == 0 || bArr.length > this.mMtu || Peripheral.this.mSender == null || !Peripheral.this.mSender.push(this.mBluetoothDevice, bArr)) {
                return false;
            }
            Peripheral.this.mSender.requestSend();
            return true;
        }
    }

    public enum State {
        UNSUPPORTED,
        ACTIVATING,
        ACTIVATED,
        INACTIVATING,
        INACTIVATED
    }

    public Peripheral(Config config, Context context) throws IllegalArgumentException {
        Context context2;
        UUID uuidRandomUUID = UUID.randomUUID();
        this.mUuid = uuidRandomUUID;
        this.mState = State.UNSUPPORTED;
        this.mAdvertiseState = AdvertiseState.INACTIVATED;
        this.mSocketMap = new ConcurrentHashMap();
        this.mAdvertiseCallback = new AdvertiseCallback() { // from class: jp.konami.peerlink.ble.Peripheral.1
            @Override // android.bluetooth.le.AdvertiseCallback
            public void onStartFailure(int i) {
                Logger.m968e(Peripheral.TAG, "Failed to start advertise. (errorCode = " + i + ")");
                Peripheral.this.mAdvertiseState = AdvertiseState.INACTIVATED;
            }

            @Override // android.bluetooth.le.AdvertiseCallback
            public void onStartSuccess(AdvertiseSettings advertiseSettings) {
                Logger.m968e(Peripheral.TAG, "Succeed in start advertise. (settingsInEffect = " + advertiseSettings.toString() + ")");
                Peripheral.this.mAdvertiseState = AdvertiseState.ACTIVATED;
            }
        };
        BluetoothGattServerCallback bluetoothGattServerCallback = new BluetoothGattServerCallback() { // from class: jp.konami.peerlink.ble.Peripheral.2
            @Override // android.bluetooth.BluetoothGattServerCallback
            public void onCharacteristicReadRequest(BluetoothDevice bluetoothDevice, int i, int i2, BluetoothGattCharacteristic bluetoothGattCharacteristic) {
                if (Peripheral.this.mBluetoothGattServer == null) {
                    Logger.m968e(Peripheral.TAG, "Unknown error.");
                    return;
                }
                Socket socket = (Socket) Peripheral.this.mSocketMap.get(bluetoothDevice);
                if (socket == null) {
                    Peripheral.this.abort(bluetoothDevice);
                } else {
                    socket.onCharacteristicReadRequest(bluetoothDevice, i, i2, bluetoothGattCharacteristic);
                }
            }

            @Override // android.bluetooth.BluetoothGattServerCallback
            public void onCharacteristicWriteRequest(BluetoothDevice bluetoothDevice, int i, BluetoothGattCharacteristic bluetoothGattCharacteristic, boolean z, boolean z2, int i2, byte[] bArr) {
                if (Peripheral.this.mBluetoothGattServer == null) {
                    Logger.m968e(Peripheral.TAG, "Unknown error.");
                    return;
                }
                Socket socket = (Socket) Peripheral.this.mSocketMap.get(bluetoothDevice);
                if (socket == null) {
                    Peripheral.this.abort(bluetoothDevice);
                } else {
                    socket.onCharacteristicWriteRequest(bluetoothDevice, i, bluetoothGattCharacteristic, z, z2, i2, bArr);
                }
            }

            @Override // android.bluetooth.BluetoothGattServerCallback
            public void onConnectionStateChange(BluetoothDevice bluetoothDevice, int i, int i2) {
                if (Peripheral.this.mBluetoothGattServer == null) {
                    Logger.m968e(Peripheral.TAG, "Unknown error.");
                    return;
                }
                if (i != 0) {
                    Peripheral.this.abort(bluetoothDevice);
                    return;
                }
                if (i2 == 0) {
                    Peripheral.this.unregisterSocket(bluetoothDevice);
                } else if (i2 == 2 && !Peripheral.this.registerSocket(bluetoothDevice)) {
                    Peripheral.this.abort(bluetoothDevice);
                }
            }

            @Override // android.bluetooth.BluetoothGattServerCallback
            public void onDescriptorReadRequest(BluetoothDevice bluetoothDevice, int i, int i2, BluetoothGattDescriptor bluetoothGattDescriptor) {
                if (Peripheral.this.mBluetoothGattServer == null) {
                    Logger.m968e(Peripheral.TAG, "Unknown error.");
                    return;
                }
                Socket socket = (Socket) Peripheral.this.mSocketMap.get(bluetoothDevice);
                if (socket == null) {
                    Peripheral.this.abort(bluetoothDevice);
                } else {
                    socket.onDescriptorReadRequest(bluetoothDevice, i, i2, bluetoothGattDescriptor);
                }
            }

            @Override // android.bluetooth.BluetoothGattServerCallback
            public void onDescriptorWriteRequest(BluetoothDevice bluetoothDevice, int i, BluetoothGattDescriptor bluetoothGattDescriptor, boolean z, boolean z2, int i2, byte[] bArr) {
                if (Peripheral.this.mBluetoothGattServer == null) {
                    Logger.m968e(Peripheral.TAG, "Unknown error.");
                    return;
                }
                Socket socket = (Socket) Peripheral.this.mSocketMap.get(bluetoothDevice);
                if (socket == null) {
                    Peripheral.this.abort(bluetoothDevice);
                } else {
                    socket.onDescriptorWriteRequest(bluetoothDevice, i, bluetoothGattDescriptor, z, z2, i2, bArr);
                }
            }

            @Override // android.bluetooth.BluetoothGattServerCallback
            public void onExecuteWrite(BluetoothDevice bluetoothDevice, int i, boolean z) {
                if (Peripheral.this.mBluetoothGattServer == null) {
                    Logger.m968e(Peripheral.TAG, "Unknown error.");
                    return;
                }
                Socket socket = (Socket) Peripheral.this.mSocketMap.get(bluetoothDevice);
                if (socket == null) {
                    Peripheral.this.abort(bluetoothDevice);
                } else {
                    socket.onExecuteWrite(bluetoothDevice, i, z);
                }
            }

            @Override // android.bluetooth.BluetoothGattServerCallback
            public void onMtuChanged(BluetoothDevice bluetoothDevice, int i) {
                if (Peripheral.this.mBluetoothGattServer == null) {
                    Logger.m968e(Peripheral.TAG, "Unknown error.");
                    return;
                }
                Socket socket = (Socket) Peripheral.this.mSocketMap.get(bluetoothDevice);
                if (socket == null) {
                    Peripheral.this.abort(bluetoothDevice);
                } else {
                    socket.onMtuChanged(bluetoothDevice, i);
                }
            }

            @Override // android.bluetooth.BluetoothGattServerCallback
            public void onNotificationSent(BluetoothDevice bluetoothDevice, int i) {
                if (Peripheral.this.mBluetoothGattServer == null) {
                    Logger.m968e(Peripheral.TAG, "Unknown error.");
                } else if (Peripheral.this.mSender == null) {
                    Logger.m968e(Peripheral.TAG, "Unknown error.");
                } else {
                    Peripheral.this.mSender.onNotificationSent(bluetoothDevice, i);
                }
            }

            @Override // android.bluetooth.BluetoothGattServerCallback
            public void onServiceAdded(int i, BluetoothGattService bluetoothGattService) {
                if (Peripheral.this.mBluetoothGattServer == null) {
                    Logger.m968e(Peripheral.TAG, "Unknown error.");
                } else {
                    Logger.m967d(Peripheral.TAG, "onServiceAdded: status = " + i + ", service = " + bluetoothGattService.getUuid().toString());
                }
            }
        };
        this.mBluetoothGattServerCallback = bluetoothGattServerCallback;
        this.mConfig = config;
        this.mContext = context;
        if (!config.isValid() || (context2 = this.mContext) == null) {
            Logger.m968e(TAG, "Invalid argument.");
            throw new IllegalArgumentException("Invalid argument.");
        }
        if (!context2.getPackageManager().hasSystemFeature("android.hardware.bluetooth_le")) {
            this.mState = State.UNSUPPORTED;
            return;
        }
        BluetoothManager bluetoothManager = (BluetoothManager) this.mContext.getSystemService("bluetooth");
        this.mBluetoothManager = bluetoothManager;
        if (bluetoothManager == null) {
            this.mState = State.UNSUPPORTED;
            return;
        }
        BluetoothAdapter adapter = bluetoothManager.getAdapter();
        this.mBluetoothAdapter = adapter;
        if (adapter == null || !adapter.isEnabled()) {
            this.mState = State.INACTIVATED;
            return;
        }
        if (!isCapableToAdvertise(this.mBluetoothAdapter)) {
            Logger.m968e(TAG, "Unsupported peripheral mode.");
            this.mState = State.UNSUPPORTED;
            return;
        }
        BluetoothLeAdvertiser bluetoothLeAdvertiser = this.mBluetoothAdapter.getBluetoothLeAdvertiser();
        this.mBluetoothLeAdvertiser = bluetoothLeAdvertiser;
        if (bluetoothLeAdvertiser == null) {
            this.mState = State.INACTIVATED;
            return;
        }
        BluetoothGattService bluetoothGattService = new BluetoothGattService(UUID.fromString(this.mConfig.getServiceUuid()), 0);
        BluetoothGattCharacteristic bluetoothGattCharacteristic = new BluetoothGattCharacteristic(UUID.fromString(this.mConfig.getPeripheralAdvertisementUuid()), 2, 1);
        BluetoothGattCharacteristic bluetoothGattCharacteristic2 = new BluetoothGattCharacteristic(UUID.fromString(this.mConfig.getCentralAdvertisementUuid()), 8, 16);
        BluetoothGattCharacteristic bluetoothGattCharacteristic3 = new BluetoothGattCharacteristic(UUID.fromString(this.mConfig.getUplinkUuid()), 4, 16);
        BluetoothGattCharacteristic bluetoothGattCharacteristic4 = new BluetoothGattCharacteristic(UUID.fromString(this.mConfig.getDownlinkUuid()), 16, 1);
        BluetoothGattDescriptor bluetoothGattDescriptor = new BluetoothGattDescriptor(uuidRandomUUID, 0);
        BluetoothGattDescriptor bluetoothGattDescriptor2 = new BluetoothGattDescriptor(UUID.fromString(CONFIG_UUID), 16);
        byte[] bArrSerialize = new AdvertisementHeader(uuidRandomUUID, this.mConfig.getServiceId(), this.mConfig.getId(), this.mConfig.getAttribute()).serialize();
        if (bArrSerialize == null) {
            this.mState = State.INACTIVATED;
            return;
        }
        if (!bluetoothGattCharacteristic.setValue(bArrSerialize)) {
            this.mState = State.INACTIVATED;
            return;
        }
        if (!bluetoothGattCharacteristic.addDescriptor(bluetoothGattDescriptor) || !bluetoothGattCharacteristic4.addDescriptor(bluetoothGattDescriptor2) || !bluetoothGattService.addCharacteristic(bluetoothGattCharacteristic) || !bluetoothGattService.addCharacteristic(bluetoothGattCharacteristic2) || !bluetoothGattService.addCharacteristic(bluetoothGattCharacteristic3) || !bluetoothGattService.addCharacteristic(bluetoothGattCharacteristic4)) {
            this.mState = State.INACTIVATED;
            return;
        }
        BluetoothGattServer bluetoothGattServerOpenGattServer = this.mBluetoothManager.openGattServer(this.mContext, bluetoothGattServerCallback);
        this.mBluetoothGattServer = bluetoothGattServerOpenGattServer;
        if (bluetoothGattServerOpenGattServer == null) {
            this.mState = State.INACTIVATED;
        } else if (!bluetoothGattServerOpenGattServer.addService(bluetoothGattService)) {
            this.mState = State.INACTIVATED;
        } else {
            this.mSender = new Sender(bluetoothGattCharacteristic4);
            this.mState = State.ACTIVATED;
        }
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void abort(BluetoothDevice bluetoothDevice) {
        if (bluetoothDevice == null) {
            return;
        }
        BluetoothGattServer bluetoothGattServer = this.mBluetoothGattServer;
        if (bluetoothGattServer != null) {
            bluetoothGattServer.cancelConnection(bluetoothDevice);
        }
        this.mSocketMap.remove(bluetoothDevice);
    }

    private static boolean isCapableToAdvertise(BluetoothAdapter bluetoothAdapter) {
        return bluetoothAdapter != null && bluetoothAdapter.getBluetoothLeAdvertiser() != null && bluetoothAdapter.isMultipleAdvertisementSupported() && bluetoothAdapter.isOffloadedFilteringSupported() && bluetoothAdapter.isOffloadedScanBatchingSupported();
    }

    /* JADX INFO: Access modifiers changed from: private */
    public boolean registerSocket(BluetoothDevice bluetoothDevice) {
        if (bluetoothDevice == null) {
            return false;
        }
        synchronized (this.mSocketMap) {
            if (this.mSocketMap.containsKey(bluetoothDevice)) {
                return false;
            }
            Socket socket = new Socket(bluetoothDevice);
            if (socket.getState() == BluetoothLowEnergySocket.State.CLOSED) {
                return false;
            }
            this.mSocketMap.put(bluetoothDevice, socket);
            return true;
        }
    }

    /* JADX INFO: Access modifiers changed from: private */
    public boolean unregisterSocket(BluetoothDevice bluetoothDevice) {
        if (bluetoothDevice == null) {
            return false;
        }
        synchronized (this.mSocketMap) {
            if (!this.mSocketMap.containsKey(bluetoothDevice)) {
                return false;
            }
            Socket socketRemove = this.mSocketMap.remove(bluetoothDevice);
            if (socketRemove == null) {
                return true;
            }
            socketRemove.destruct();
            return true;
        }
    }

    public void destruct() {
        if (!stopAdvertise()) {
            this.mAdvertiseState = AdvertiseState.INACTIVATED;
        }
        Iterator<Map.Entry<BluetoothDevice, Socket>> it = this.mSocketMap.entrySet().iterator();
        while (it.hasNext()) {
            Map.Entry<BluetoothDevice, Socket> next = it.next();
            BluetoothDevice key = next.getKey();
            if (key != null) {
                abort(key);
            }
            Socket value = next.getValue();
            if (value != null) {
                value.destruct();
            }
            it.remove();
        }
        BluetoothGattServer bluetoothGattServer = this.mBluetoothGattServer;
        if (bluetoothGattServer != null) {
            bluetoothGattServer.clearServices();
            this.mBluetoothGattServer.close();
        }
        this.mState = State.INACTIVATED;
    }

    public AdvertiseState getAdvertiseState() {
        return this.mAdvertiseState;
    }

    public List<BluetoothLowEnergySocket> getConnectionRequestedSocketList() {
        if (this.mSocketMap.isEmpty()) {
            return null;
        }
        ArrayList arrayList = new ArrayList();
        for (Socket socket : this.mSocketMap.values()) {
            if (socket != null && socket.getState() == BluetoothLowEnergySocket.State.CONNECTING) {
                arrayList.add(socket);
            }
        }
        if (arrayList.isEmpty()) {
            return null;
        }
        return arrayList;
    }

    public State getState() {
        return this.mState;
    }

    public boolean startAdvertise() {
        if (this.mBluetoothLeAdvertiser == null || this.mState != State.ACTIVATED || this.mAdvertiseState != AdvertiseState.INACTIVATED) {
            return false;
        }
        this.mBluetoothLeAdvertiser.startAdvertising(new AdvertiseSettings.Builder().setAdvertiseMode(2).setConnectable(true).setTimeout(0).setTxPowerLevel(3).build(), new AdvertiseData.Builder().addServiceUuid(new ParcelUuid(UUID.fromString(this.mConfig.getServiceUuid()))).build(), this.mAdvertiseCallback);
        this.mAdvertiseState = AdvertiseState.ACTIVATING;
        return true;
    }

    public boolean stopAdvertise() {
        if (this.mBluetoothLeAdvertiser == null || this.mState != State.ACTIVATED || this.mAdvertiseState != AdvertiseState.ACTIVATED) {
            return false;
        }
        this.mBluetoothLeAdvertiser.stopAdvertising(this.mAdvertiseCallback);
        this.mAdvertiseState = AdvertiseState.INACTIVATED;
        return true;
    }
}

===== managed-work/jadx/sources/jp/konami/peerlink/btc/BluetoothClassic.java =====
package jp.konami.peerlink.btc;

import android.app.Activity;
import android.app.AlertDialog;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothDevice;
import android.bluetooth.BluetoothServerSocket;
import android.bluetooth.BluetoothSocket;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.DialogInterface;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.res.Resources;
import android.os.Build;
import android.os.ParcelUuid;
import android.os.Parcelable;
import androidx.core.app.ActivityCompat;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.lang.Thread;
import java.nio.ByteBuffer;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Queue;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.ScheduledFuture;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import jp.konami.Logger;
import org.json.JSONException;
import org.json.JSONObject;

/* JADX INFO: loaded from: classes3.dex */
public class BluetoothClassic {
    static final String BLUETOOTH_DEVICE_DISABLED = "JP_KONAMI_PEERLINK_BTC_BLUETOOTHCLASSIC_BLUETOOTH_DEVICE_DISABLED";
    static final String BLUETOOTH_DEVICE_ENABLED = "JP_KONAMI_PEERLINK_BTC_BLUETOOTHCLASSIC_BLUETOOTH_DEVICE_ENABLED";
    static final String BLUETOOTH_DISCOVERABLE_MODE_DISABLED = "JP_KONAMI_PEERLINK_BTC_BLUETOOTHCLASSIC_BLUETOOTH_DISCOVERABLE_MODE_DISABLED";
    static final String BLUETOOTH_DISCOVERABLE_MODE_ENABLED = "JP_KONAMI_PEERLINK_BTC_BLUETOOTHCLASSIC_BLUETOOTH_DISCOVERABLE_MODE_ENABLED";
    private static final int BUFFER_LENGTH = 2048;
    private static final int CONNECTION_TIMEOUT_MS = 3000;
    private static final int MAX_ADVERTISE_DATA_LENGTH = 1500;
    private static final int MAX_DATA_LENGTH = 1500;
    private static final int MAX_QUEUE_SIZE = 100;
    static final String PERMISSION_DENIED = "JP_KONAMI_PEERLINK_BTC_BLUETOOTHCLASSIC_PERMISSION_DENIED";
    static final String PERMISSION_EXPLANATION_REQUIERED = "JP_KONAMI_PEERLINK_BTC_BLUETOOTHCLASSIC_PERMISSION_EPLANATION_REQUIERED";
    static final String PERMISSION_GRANTED = "JP_KONAMI_PEERLINK_BTC_BLUETOOTHCLASSIC_PERMISSION_GRANTED";
    static final String PERMISSION_REQUEST = "JP_KONAMI_PEERLINK_BTC_BLUETOOTHCLASSIC_PERMISSION_REQUEST";
    private static final String TAG = "BluetoothClassic";
    private Activity mActivity;
    private AdvertiseThread mAdvertiseThread;
    private Config mConfig;
    private ConnectThread mConnectThread;
    private ConnectionThreadController mConnectionThreadController;
    private DeviceState mDeviceState;
    private ListenThread mListenThread;
    private Receiver mReceiver;
    private ScanThread mScanThread;
    private BluetoothAdapter mBluetoothAdapter = BluetoothAdapter.getDefaultAdapter();
    private DiscoveryState mDiscoveryState = DiscoveryState.INACTIVATED;
    private DiscoverableState mDiscoverableState = DiscoverableState.INACTIVATED;
    private final Set<DeviceInfo> mFoundNodes = new HashSet();

    private class AdvertiseThread extends Thread {
        private BluetoothServerSocket mSocket;

        public AdvertiseThread() throws IOException {
            this.mSocket = BluetoothClassic.this.mBluetoothAdapter.listenUsingInsecureRfcommWithServiceRecord(BluetoothClassic.this.mConfig.getServiceId(), UUID.fromString(BluetoothClassic.this.mConfig.getControlConnectionUuid()));
        }

        public void cancel() {
            try {
                this.mSocket.close();
                join();
            } catch (IOException unused) {
                Logger.m968e(BluetoothClassic.TAG, "Failed to close.");
                this.mSocket = null;
            } catch (InterruptedException unused2) {
                this.mSocket = null;
            }
        }

        protected void finalize() {
            cancel();
        }

        @Override // java.lang.Thread, java.lang.Runnable
        public void run() {
            BluetoothSocket bluetoothSocketAccept;
            while (true) {
                bluetoothSocketAccept = null;
                try {
                    try {
                        bluetoothSocketAccept = this.mSocket.accept();
                    } catch (Throwable th) {
                        if (0 != 0) {
                            try {
                                bluetoothSocketAccept.close();
                            } catch (IOException e) {
                                Logger.m968e(BluetoothClassic.TAG, "Unknown error.");
                                e.printStackTrace();
                            }
                        }
                        throw th;
                    }
                } catch (IOException e2) {
                    Logger.m968e(BluetoothClassic.TAG, "Advertise failed.");
                    e2.printStackTrace();
                    if (0 == 0) {
                        return;
                    }
                } catch (InterruptedException e3) {
                    Logger.m968e(BluetoothClassic.TAG, "Advertise failed.");
                    e3.printStackTrace();
                    if (0 != 0) {
                    }
                }
                if (bluetoothSocketAccept == null) {
                    break;
                }
                DatagramBluetoothSocket datagramBluetoothSocket = BluetoothClassic.this.new DatagramBluetoothSocket(bluetoothSocketAccept);
                Logger.m967d(BluetoothClassic.TAG, "Control connection accepted: " + datagramBluetoothSocket.getRemoteDevice().toString());
                if (BluetoothClassic.this.sendAdvertise(datagramBluetoothSocket)) {
                    long jCurrentTimeMillis = System.currentTimeMillis();
                    while (true) {
                        if (!datagramBluetoothSocket.isConnected()) {
                            break;
                        }
                        if (System.currentTimeMillis() - jCurrentTimeMillis >= BluetoothClassic.this.mConfig.getAdvertiseTimeoutMs()) {
                            Logger.m968e(BluetoothClassic.TAG, "Advertise timedout.");
                            break;
                        }
                        Thread.sleep(BluetoothClassic.this.mConfig.getAdvertiseTimeoutMs() < 100 ? BluetoothClassic.this.mConfig.getAdvertiseTimeoutMs() : 100L);
                    }
                }
                if (bluetoothSocketAccept != null) {
                    try {
                        bluetoothSocketAccept.close();
                    } catch (IOException e4) {
                        Logger.m968e(BluetoothClassic.TAG, "Unknown error.");
                        e4.printStackTrace();
                    }
                }
            }
            if (bluetoothSocketAccept == null) {
                return;
            }
            try {
                bluetoothSocketAccept.close();
            } catch (IOException e5) {
                Logger.m968e(BluetoothClassic.TAG, "Unknown error.");
                e5.printStackTrace();
            }
        }
    }

    public static class Config {
        private Map mAttribute;
        private String mControlConnectionUuid;
        private String mDataConnectionUuid;
        private String mId;
        private String mServiceId;
        private int mAdvertiseTimeoutMs = 1000;
        private int mScanWaitTimeoutMs = 10000;

        /* JADX INFO: Access modifiers changed from: private */
        public boolean isValid() {
            String str;
            String str2;
            String str3;
            String str4 = this.mServiceId;
            return (str4 == null || str4.isEmpty() || (str = this.mId) == null || str.isEmpty() || (str2 = this.mControlConnectionUuid) == null || str2.isEmpty() || (str3 = this.mDataConnectionUuid) == null || str3.isEmpty()) ? false : true;
        }

        public int getAdvertiseTimeoutMs() {
            return this.mAdvertiseTimeoutMs;
        }

        public Map<String, String> getAttribute() {
            return this.mAttribute;
        }

        public String getControlConnectionUuid() {
            return this.mControlConnectionUuid;
        }

        public String getDataConnectionUuid() {
            return this.mDataConnectionUuid;
        }

        public String getId() {
            return this.mId;
        }

        public String getServiceId() {
            return this.mServiceId;
        }

        public void setAdvertiseTimeoutMs(int i) {
            this.mAdvertiseTimeoutMs = i;
        }

        public void setAttribute(String str, String str2) {
            if (this.mAttribute == null) {
                this.mAttribute = new HashMap();
            }
            this.mAttribute.put(str, str2);
        }

        public void setControlConnectionUuid(String str) {
            this.mControlConnectionUuid = str;
        }

        public void setDataConnectionUuid(String str) {
            this.mDataConnectionUuid = str;
        }

        public void setId(String str) {
            this.mId = str;
        }

        public void setServiceId(String str) {
            this.mServiceId = str;
        }
    }

    private class ConnectThread extends Thread {
        private BluetoothSocket mSocket;

        public ConnectThread(BluetoothDevice bluetoothDevice) throws IOException, IllegalArgumentException {
            if (bluetoothDevice == null) {
                throw new IllegalArgumentException("Invalid argument.");
            }
            this.mSocket = bluetoothDevice.createInsecureRfcommSocketToServiceRecord(UUID.fromString(BluetoothClassic.this.mConfig.getDataConnectionUuid()));
        }

        public void cancel() {
            try {
                BluetoothSocket bluetoothSocket = this.mSocket;
                if (bluetoothSocket != null) {
                    bluetoothSocket.close();
                }
                join();
            } catch (IOException unused) {
                Logger.m968e(BluetoothClassic.TAG, "Failed to close.");
                this.mSocket = null;
            } catch (InterruptedException unused2) {
                this.mSocket = null;
            }
        }

        protected void finalize() {
            cancel();
        }

        @Override // java.lang.Thread, java.lang.Runnable
        public void run() {
            if (BluetoothClassic.this.mBluetoothAdapter.isDiscovering()) {
                Logger.m968e(BluetoothClassic.TAG, "Can not connect in discovering.");
                return;
            }
            try {
                this.mSocket.connect();
                DatagramBluetoothSocket datagramBluetoothSocket = BluetoothClassic.this.new DatagramBluetoothSocket(this.mSocket);
                Logger.m967d(BluetoothClassic.TAG, "Connected to " + datagramBluetoothSocket.getRemoteDevice().toString());
                if (!BluetoothClassic.this.sendAdvertise(datagramBluetoothSocket)) {
                    Logger.m968e(BluetoothClassic.TAG, "Failed to send advertise.");
                    datagramBluetoothSocket.close();
                } else {
                    BluetoothClassic.this.mConnectionThreadController = BluetoothClassic.this.new ConnectionThreadController(datagramBluetoothSocket);
                    BluetoothClassic.this.mConnectionThreadController.start();
                }
            } catch (IOException e) {
                Logger.m968e(BluetoothClassic.TAG, "Connect failed.");
                e.printStackTrace();
                try {
                    this.mSocket.close();
                } catch (IOException e2) {
                    Logger.m968e(BluetoothClassic.TAG, "Unknown error.");
                    e2.printStackTrace();
                }
            }
        }
    }

    public enum ConnectionState {
        OPEN,
        CONNECTING,
        ESTABLISHED,
        CLOSED
    }

    private class ConnectionThreadController {
        private RecvThread mRecvThread;
        private SendThread mSendThread;
        private DatagramBluetoothSocket mSocket;
        private Queue<byte[]> mRecvQueue = new ArrayDeque();
        private BlockingQueue<byte[]> mSendQueue = new ArrayBlockingQueue(100);

        private class RecvThread extends Thread {
            private Queue<byte[]> mRecvQueue;
            private DatagramBluetoothSocket mSocket;

            public RecvThread(DatagramBluetoothSocket datagramBluetoothSocket, Queue<byte[]> queue) throws IllegalArgumentException {
                if (datagramBluetoothSocket == null || !datagramBluetoothSocket.isConnected()) {
                    throw new IllegalArgumentException("Invalid argument.");
                }
                try {
                    setPriority(10);
                } catch (SecurityException unused) {
                    Logger.m968e(BluetoothClassic.TAG, "Failed to set priority.");
                }
                this.mSocket = datagramBluetoothSocket;
                this.mRecvQueue = queue;
            }

            @Override // java.lang.Thread, java.lang.Runnable
            public void run() {
                byte[] bArrRecv;
                try {
                    synchronized (this.mRecvQueue) {
                        this.mRecvQueue.clear();
                    }
                    while (this.mSocket.isConnected()) {
                        synchronized (this.mRecvQueue) {
                            if (this.mRecvQueue.size() >= 100 || (bArrRecv = this.mSocket.recv()) == null || bArrRecv.length == 0) {
                                try {
                                    Thread.sleep(1L);
                                } catch (InterruptedException e) {
                                    e.printStackTrace();
                                }
                            } else {
                                this.mRecvQueue.add(bArrRecv);
                            }
                        }
                    }
                    this.mSocket.close();
                    synchronized (this.mRecvQueue) {
                        this.mRecvQueue.clear();
                    }
                } catch (Throwable th) {
                    this.mSocket.close();
                    synchronized (this.mRecvQueue) {
                        this.mRecvQueue.clear();
                        throw th;
                    }
                }
            }
        }

        private class SendThread extends Thread {
            private BlockingQueue<byte[]> mSendQueue;
            private DatagramBluetoothSocket mSocket;

            public SendThread(DatagramBluetoothSocket datagramBluetoothSocket, BlockingQueue<byte[]> blockingQueue) throws IllegalArgumentException {
                if (datagramBluetoothSocket == null || !datagramBluetoothSocket.isConnected()) {
                    throw new IllegalArgumentException("Invalid argument.");
                }
                try {
                    setPriority(10);
                } catch (SecurityException unused) {
                    Logger.m968e(BluetoothClassic.TAG, "Failed to set priority.");
                }
                this.mSocket = datagramBluetoothSocket;
                this.mSendQueue = blockingQueue;
            }

            @Override // java.lang.Thread, java.lang.Runnable
            public void run() {
                DatagramBluetoothSocket datagramBluetoothSocket;
                try {
                    try {
                        this.mSendQueue.clear();
                        while (true) {
                            boolean zIsConnected = this.mSocket.isConnected();
                            datagramBluetoothSocket = this.mSocket;
                            if (!zIsConnected) {
                                break;
                            } else if (!datagramBluetoothSocket.send(this.mSendQueue.take())) {
                                Logger.m968e(BluetoothClassic.TAG, "Failed to send.");
                            }
                        }
                        datagramBluetoothSocket.close();
                    } catch (InterruptedException e) {
                        e.printStackTrace();
                        this.mSocket.close();
                    }
                    this.mSendQueue.clear();
                } catch (Throwable th) {
                    this.mSocket.close();
                    this.mSendQueue.clear();
                    throw th;
                }
            }
        }

        public ConnectionThreadController(DatagramBluetoothSocket datagramBluetoothSocket) throws IllegalArgumentException {
            this.mSocket = datagramBluetoothSocket;
            this.mSendThread = new SendThread(this.mSocket, this.mSendQueue);
            this.mRecvThread = new RecvThread(this.mSocket, this.mRecvQueue);
        }

        public void cancel() {
            try {
                DatagramBluetoothSocket datagramBluetoothSocket = this.mSocket;
                if (datagramBluetoothSocket != null) {
                    datagramBluetoothSocket.close();
                }
                this.mSendThread.interrupt();
                this.mSendThread.join();
                this.mRecvThread.join();
            } catch (InterruptedException unused) {
                this.mSocket = null;
            }
        }

        protected void finalize() {
            cancel();
        }

        public boolean isAlive() {
            return this.mSendThread.isAlive() && this.mRecvThread.isAlive();
        }

        public void start() {
            this.mSendThread.start();
            this.mRecvThread.start();
        }
    }

    private class DatagramBluetoothSocket {
        private InputStream mInputStream;
        private OutputStream mOutputStream;
        private final byte[] mRecvBuffer = new byte[2048];
        private int mRecvBufferUseLength = 0;
        private BluetoothSocket mSocket;

        public DatagramBluetoothSocket(BluetoothSocket bluetoothSocket) throws IOException {
            OutputStream outputStream;
            InputStream inputStream;
            OutputStream outputStream2 = null;
            InputStream inputStream2 = null;
            this.mOutputStream = null;
            this.mInputStream = null;
            this.mSocket = bluetoothSocket;
            if (bluetoothSocket != null) {
                try {
                    outputStream = bluetoothSocket.getOutputStream();
                } catch (IOException e) {
                    e = e;
                    outputStream = null;
                }
                try {
                    inputStream = this.mSocket.getInputStream();
                    outputStream2 = outputStream;
                } catch (IOException e2) {
                    e = e2;
                    Logger.m968e(BluetoothClassic.TAG, "Failed to initialize.");
                    e.printStackTrace();
                }
            } else {
                inputStream = null;
            }
            InputStream inputStream3 = inputStream;
            outputStream = outputStream2;
            inputStream2 = inputStream3;
            this.mOutputStream = outputStream;
            this.mInputStream = inputStream2;
        }

        public void close() {
            BluetoothSocket bluetoothSocket = this.mSocket;
            if (bluetoothSocket == null) {
                return;
            }
            try {
                bluetoothSocket.close();
            } catch (IOException e) {
                Logger.m968e(BluetoothClassic.TAG, "Unknown error.");
                e.printStackTrace();
            }
            this.mSocket = null;
        }

        protected void finalize() {
            close();
        }

        public BluetoothDevice getRemoteDevice() {
            if (isConnected()) {
                return this.mSocket.getRemoteDevice();
            }
            return null;
        }

        public boolean isConnected() {
            BluetoothSocket bluetoothSocket = this.mSocket;
            return bluetoothSocket != null && bluetoothSocket.isConnected();
        }

        public byte[] recv() {
            if (this.mRecvBufferUseLength < 0) {
                Logger.m968e(BluetoothClassic.TAG, "Unknown error.");
                return null;
            }
            if (this.mInputStream == null || !isConnected()) {
                if (this.mRecvBufferUseLength == 0) {
                    return null;
                }
            } else if (this.mRecvBuffer.length > this.mRecvBufferUseLength) {
                try {
                    if (this.mInputStream.available() != 0) {
                        InputStream inputStream = this.mInputStream;
                        byte[] bArr = this.mRecvBuffer;
                        int i = this.mRecvBufferUseLength;
                        int i2 = inputStream.read(bArr, i, bArr.length - i);
                        if (i2 < 0) {
                            close();
                        } else {
                            this.mRecvBufferUseLength += i2;
                        }
                    }
                } catch (IOException e) {
                    Logger.m968e(BluetoothClassic.TAG, "Failed to recv.");
                    e.printStackTrace();
                }
            }
            ProtocolHeader protocolHeader = new ProtocolHeader();
            int iDeserialize = protocolHeader.Deserialize(this.mRecvBuffer, this.mRecvBufferUseLength);
            byte[] bArr2 = this.mRecvBuffer;
            if (iDeserialize > 0) {
                System.arraycopy(bArr2, iDeserialize, bArr2, 0, this.mRecvBufferUseLength - iDeserialize);
                this.mRecvBufferUseLength -= iDeserialize;
                return protocolHeader.getData();
            }
            if (bArr2.length <= this.mRecvBufferUseLength) {
                Logger.m968e(BluetoothClassic.TAG, "Protocol violation.");
                close();
            }
            return null;
        }

        public boolean send(byte[] bArr) {
            if (this.mOutputStream != null && isConnected()) {
                ProtocolHeader protocolHeader = new ProtocolHeader();
                if (!protocolHeader.setData(bArr)) {
                    Logger.m968e(BluetoothClassic.TAG, "Failed to serialize.");
                    return false;
                }
                byte[] bArrSerialize = protocolHeader.Serialize();
                if (bArrSerialize != null && bArrSerialize.length != 0) {
                    try {
                        this.mOutputStream.write(bArrSerialize);
                        this.mOutputStream.flush();
                        return true;
                    } catch (IOException e) {
                        Logger.m968e(BluetoothClassic.TAG, "Failed to send.");
                        e.printStackTrace();
                        return false;
                    }
                }
                Logger.m968e(BluetoothClassic.TAG, "Failed to serialize.");
            }
            return false;
        }
    }

    public static class DeviceInfo {
        private Map mAttribute;
        private BluetoothDevice mDevice;
        private String mId;

        private DeviceInfo(BluetoothDevice bluetoothDevice, String str, Map map) {
            this.mDevice = bluetoothDevice;
            this.mId = str;
            this.mAttribute = map;
        }

        /* JADX INFO: Access modifiers changed from: private */
        public BluetoothDevice getDevice() {
            return this.mDevice;
        }

        public boolean equals(Object obj) {
            if (obj == null) {
                return false;
            }
            if (!(obj instanceof DeviceInfo)) {
                return super.equals(obj);
            }
            DeviceInfo deviceInfo = (DeviceInfo) obj;
            BluetoothDevice bluetoothDevice = this.mDevice;
            if (bluetoothDevice != null ? bluetoothDevice.equals(deviceInfo.mDevice) : deviceInfo.mDevice == null) {
                String str = this.mId;
                if (str != null ? str.equals(deviceInfo.mId) : deviceInfo.mId == null) {
                    Map map = this.mAttribute;
                    Map map2 = deviceInfo.mAttribute;
                    if (map == null) {
                        if (map2 == null) {
                            return true;
                        }
                    } else if (map.equals(map2)) {
                        return true;
                    }
                }
            }
            return false;
        }

        public Map<String, String> getAttribute() {
            return this.mAttribute;
        }

        public String getId() {
            return this.mId;
        }

        public int hashCode() {
            BluetoothDevice bluetoothDevice = this.mDevice;
            int iHashCode = bluetoothDevice == null ? 0 : bluetoothDevice.hashCode();
            String str = this.mId;
            int iHashCode2 = iHashCode + (str == null ? 0 : str.hashCode());
            Map map = this.mAttribute;
            return iHashCode2 + (map != null ? map.hashCode() : 0);
        }
    }

    public enum DeviceState {
        UNSUPPORTED,
        ACTIVATING,
        ACTIVATED,
        INACTIVATING,
        INACTIVATED
    }

    public enum DiscoverableState {
        ACTIVATING,
        ACTIVATED,
        INACTIVATING,
        INACTIVATED
    }

    public enum DiscoveryState {
        ACTIVATING,
        ACTIVATED,
        INACTIVATING,
        INACTIVATED
    }

    private class ListenThread extends Thread {
        private final BlockingQueue<BluetoothSocket> mAcceptedQueue = new ArrayBlockingQueue(1);
        private BluetoothServerSocket mSocket;

        public ListenThread() throws IOException {
            this.mSocket = BluetoothClassic.this.mBluetoothAdapter.listenUsingInsecureRfcommWithServiceRecord(BluetoothClassic.this.mConfig.getServiceId(), UUID.fromString(BluetoothClassic.this.mConfig.getDataConnectionUuid()));
        }

        public DeviceInfo accept() {
            if (BluetoothClassic.this.mConnectionThreadController != null) {
                return null;
            }
            while (true) {
                BluetoothSocket bluetoothSocketPoll = this.mAcceptedQueue.poll();
                if (bluetoothSocketPoll == null) {
                    return null;
                }
                DatagramBluetoothSocket datagramBluetoothSocket = BluetoothClassic.this.new DatagramBluetoothSocket(bluetoothSocketPoll);
                DeviceInfo deviceInfoRecvAdvertise = BluetoothClassic.this.recvAdvertise(datagramBluetoothSocket);
                if (deviceInfoRecvAdvertise != null) {
                    BluetoothClassic.this.mConnectionThreadController = BluetoothClassic.this.new ConnectionThreadController(datagramBluetoothSocket);
                    BluetoothClassic.this.mConnectionThreadController.start();
                    Logger.m967d(BluetoothClassic.TAG, "Data connection accepted: " + deviceInfoRecvAdvertise.getDevice().toString());
                    return deviceInfoRecvAdvertise;
                }
                datagramBluetoothSocket.close();
            }
        }

        public void cancel() {
            try {
                this.mSocket.close();
                interrupt();
                join();
            } catch (IOException unused) {
                Logger.m968e(BluetoothClassic.TAG, "Failed to close.");
                this.mSocket = null;
            } catch (InterruptedException unused2) {
                this.mSocket = null;
            }
        }

        protected void finalize() {
            cancel();
        }

        @Override // java.lang.Thread, java.lang.Runnable
        public void run() {
            while (true) {
                BluetoothSocket bluetoothSocketAccept = null;
                try {
                    bluetoothSocketAccept = this.mSocket.accept();
                } catch (IOException e) {
                    Logger.m968e(BluetoothClassic.TAG, "Accept failed.");
                    e.printStackTrace();
                    if (bluetoothSocketAccept != null) {
                        try {
                            bluetoothSocketAccept.close();
                            return;
                        } catch (IOException e2) {
                            Logger.m968e(BluetoothClassic.TAG, "Unknown error.");
                            e2.printStackTrace();
                            return;
                        }
                    }
                    return;
                } catch (InterruptedException e3) {
                    e3.printStackTrace();
                }
                if (bluetoothSocketAccept == null) {
                    return;
                } else {
                    this.mAcceptedQueue.put(bluetoothSocketAccept);
                }
            }
        }
    }

    private class ProtocolHeader {
        private static final int MAX_DATA_LENGTH = 65535;
        private byte[] mData;

        private ProtocolHeader() {
            this.mData = null;
        }

        public int Deserialize(byte[] bArr) {
            if (bArr == null) {
                return 0;
            }
            return Deserialize(bArr, bArr.length);
        }

        public int Deserialize(byte[] bArr, int i) {
            ByteBuffer byteBufferWrap;
            short s;
            if (bArr == null || i < 2 || bArr.length < i || (s = (byteBufferWrap = ByteBuffer.wrap(bArr)).getShort()) == 0 || s > i - 2 || s > 65535) {
                return 0;
            }
            byte[] bArrArray = byteBufferWrap.array();
            if (bArrArray.length < s) {
                return 0;
            }
            int i2 = s + 2;
            if (setData(Arrays.copyOfRange(bArrArray, 2, i2))) {
                return i2;
            }
            return 0;
        }

        public byte[] Serialize() {
            byte[] bArr = this.mData;
            if (bArr == null || bArr.length > 65535) {
                return null;
            }
            ByteBuffer byteBufferAllocate = ByteBuffer.allocate(bArr.length + 2);
            byteBufferAllocate.putShort((short) this.mData.length);
            byteBufferAllocate.put(this.mData);
            return byteBufferAllocate.array();
        }

        public byte[] getData() {
            return this.mData;
        }

        public boolean setData(byte[] bArr) {
            if (bArr.length == 0 || bArr.length > 65535) {
                return false;
            }
            byte[] bArr2 = new byte[bArr.length];
            this.mData = bArr2;
            System.arraycopy(bArr, 0, bArr2, 0, bArr2.length);
            return true;
        }
    }

    private class Receiver extends BroadcastReceiver {
        private boolean mRegistered;

        public Receiver() {
            this.mRegistered = false;
            IntentFilter intentFilter = new IntentFilter();
            intentFilter.addAction(BluetoothClassic.BLUETOOTH_DEVICE_ENABLED);
            intentFilter.addAction(BluetoothClassic.BLUETOOTH_DEVICE_DISABLED);
            intentFilter.addAction(BluetoothClassic.BLUETOOTH_DISCOVERABLE_MODE_ENABLED);
            intentFilter.addAction(BluetoothClassic.BLUETOOTH_DISCOVERABLE_MODE_DISABLED);
            intentFilter.addAction(BluetoothClassic.PERMISSION_GRANTED);
            intentFilter.addAction(BluetoothClassic.PERMISSION_DENIED);
            intentFilter.addAction(BluetoothClassic.PERMISSION_EXPLANATION_REQUIERED);
            intentFilter.addAction(BluetoothClassic.PERMISSION_REQUEST);
            BluetoothClassic.this.mActivity.registerReceiver(this, intentFilter, 4);
            IntentFilter intentFilter2 = new IntentFilter();
            intentFilter2.addAction("android.bluetooth.adapter.action.DISCOVERY_STARTED");
            intentFilter2.addAction("android.bluetooth.adapter.action.DISCOVERY_FINISHED");
            intentFilter2.addAction("android.bluetooth.adapter.action.SCAN_MODE_CHANGED");
            intentFilter2.addAction("android.bluetooth.adapter.action.STATE_CHANGED");
            intentFilter2.addAction("android.bluetooth.adapter.action.LOCAL_NAME_CHANGED");
            intentFilter2.addAction("android.bluetooth.device.action.FOUND");
            intentFilter2.addAction("android.bluetooth.device.action.NAME_CHANGED");
            intentFilter2.addAction("android.bluetooth.device.action.UUID");
            BluetoothClassic.this.mActivity.registerReceiver(this, intentFilter2, 2);
            this.mRegistered = true;
        }

        public void destruct() {
            if (this.mRegistered) {
                this.mRegistered = false;
                BluetoothClassic.this.mActivity.unregisterReceiver(this);
            }
        }

        protected void finalize() {
            destruct();
        }

        @Override // android.content.BroadcastReceiver
        public void onReceive(Context context, Intent intent) {
            String action = intent.getAction();
            if (action.equals(BluetoothClassic.BLUETOOTH_DEVICE_ENABLED)) {
                Logger.m967d(BluetoothClassic.TAG, "Bluetooth device enabled.");
                BluetoothClassic.this.checkPermission();
                return;
            }
            if (action.equals(BluetoothClassic.BLUETOOTH_DEVICE_DISABLED)) {
                Logger.m967d(BluetoothClassic.TAG, "Bluetooth device disabled.");
                BluetoothClassic.this.mDeviceState = DeviceState.INACTIVATED;
                return;
            }
            if (action.equals(BluetoothClassic.BLUETOOTH_DISCOVERABLE_MODE_ENABLED)) {
                return;
            }
            if (action.equals(BluetoothClassic.BLUETOOTH_DISCOVERABLE_MODE_DISABLED)) {
                Logger.m967d(BluetoothClassic.TAG, "Bluetooth discoverable mode refused.");
                BluetoothClassic.this.stopDiscoverableThread();
                BluetoothClassic.this.mDiscoverableState = DiscoverableState.INACTIVATED;
                return;
            }
            if (action.equals("android.bluetooth.adapter.action.DISCOVERY_STARTED")) {
                Logger.m967d(BluetoothClassic.TAG, "Started discovery.");
                DiscoveryState discoveryState = BluetoothClassic.this.mDiscoveryState;
                DiscoveryState discoveryState2 = DiscoveryState.ACTIVATING;
                BluetoothClassic bluetoothClassic = BluetoothClassic.this;
                if (discoveryState != discoveryState2) {
                    Logger.m968e(BluetoothClassic.TAG, "Unknown error. (state = " + bluetoothClassic.mDiscoveryState + ")");
                    return;
                } else {
                    bluetoothClassic.mScanThread = BluetoothClassic.this.new ScanThread();
                    BluetoothClassic.this.mDiscoveryState = DiscoveryState.ACTIVATED;
                    return;
                }
            }
            if (action.equals("android.bluetooth.adapter.action.DISCOVERY_FINISHED")) {
                Logger.m967d(BluetoothClassic.TAG, "Finished discovery.");
                ScanThread scanThread = BluetoothClassic.this.mScanThread;
                BluetoothClassic bluetoothClassic2 = BluetoothClassic.this;
                if (scanThread == null) {
                    if (bluetoothClassic2.getDiscoveryState() != DiscoveryState.INACTIVATED) {
                        Logger.m968e(BluetoothClassic.TAG, "Unknown error.");
                        BluetoothClassic.this.stopDiscovery();
                        return;
                    }
                    return;
                }
                try {
                    bluetoothClassic2.mScanThread.start();
                    return;
                } catch (IllegalThreadStateException unused) {
                    return;
                } catch (Throwable unused2) {
                    Logger.m968e(BluetoothClassic.TAG, "Unknown error.");
                    BluetoothClassic.this.stopDiscovery();
                    return;
                }
            }
            if (action.equals("android.bluetooth.adapter.action.SCAN_MODE_CHANGED")) {
                int intExtra = intent.getIntExtra("android.bluetooth.adapter.extra.PREVIOUS_SCAN_MODE", -1);
                int intExtra2 = intent.getIntExtra("android.bluetooth.adapter.extra.SCAN_MODE", -1);
                if (intExtra == -1 || intExtra2 == -1) {
                    Logger.m967d(BluetoothClassic.TAG, "Scan mode changed: Unknown error. (" + intExtra + " -> " + intExtra2 + ")");
                } else {
                    Logger.m967d(BluetoothClassic.TAG, "Scan mode changed: " + intExtra + " -> " + intExtra2);
                }
                if (intExtra2 == 23) {
                    if (BluetoothClassic.this.mDiscoverableState == DiscoverableState.ACTIVATING) {
                        Logger.m967d(BluetoothClassic.TAG, "Bluetooth discoverable mode enabled.");
                        BluetoothClassic.this.mDiscoverableState = DiscoverableState.ACTIVATED;
                        return;
                    }
                    return;
                }
                if ((intExtra2 == 20 || intExtra2 == 21) && BluetoothClassic.this.mDiscoverableState != DiscoverableState.INACTIVATED) {
                    Logger.m967d(BluetoothClassic.TAG, "Bluetooth discoverable mode disabled.");
                    if (!BluetoothClassic.this.stopDiscoverableThread()) {
                        Logger.m968e(BluetoothClassic.TAG, "Unknown error.");
                    }
                    BluetoothClassic.this.mDiscoverableState = DiscoverableState.INACTIVATED;
                    return;
                }
                return;
            }
            if (action.equals("android.bluetooth.adapter.action.STATE_CHANGED")) {
                int intExtra3 = intent.getIntExtra("android.bluetooth.adapter.extra.PREVIOUS_STATE", -1);
                int intExtra4 = intent.getIntExtra("android.bluetooth.adapter.extra.STATE", -1);
                if (intExtra3 == -1 || intExtra4 == -1) {
                    Logger.m967d(BluetoothClassic.TAG, "State changed: Unknown error. (" + intExtra3 + " -> " + intExtra4 + ")");
                    return;
                } else {
                    Logger.m967d(BluetoothClassic.TAG, "State changed: " + intExtra3 + " -> " + intExtra4);
                    return;
                }
            }
            if (action.equals("android.bluetooth.adapter.action.LOCAL_NAME_CHANGED")) {
                Logger.m967d(BluetoothClassic.TAG, "Change name: " + intent.getStringExtra("android.bluetooth.adapter.extra.LOCAL_NAME"));
                return;
            }
            if (action.equals("android.bluetooth.device.action.FOUND")) {
                Logger.m967d(BluetoothClassic.TAG, "Device found: " + ((BluetoothDevice) intent.getParcelableExtra("android.bluetooth.device.extra.DEVICE")).toString());
                return;
            }
            if (action.equals("android.bluetooth.device.action.NAME_CHANGED")) {
                BluetoothDevice bluetoothDevice = (BluetoothDevice) intent.getParcelableExtra("android.bluetooth.device.extra.DEVICE");
                Logger.m967d(BluetoothClassic.TAG, "Device name changed: " + bluetoothDevice.toString());
                if (BluetoothClassic.this.mScanThread == null) {
                    Logger.m967d(BluetoothClassic.TAG, "Ignore device: " + bluetoothDevice.toString());
                    return;
                } else {
                    BluetoothClassic.this.mScanThread.pushFoundDevice(bluetoothDevice);
                    return;
                }
            }
            if (action.equals("android.bluetooth.device.action.UUID")) {
                if (BluetoothClassic.this.mScanThread == null) {
                    if (BluetoothClassic.this.getDiscoveryState() != DiscoveryState.INACTIVATED) {
                        Logger.m968e(BluetoothClassic.TAG, "Unknown error.");
                        BluetoothClassic.this.stopDiscovery();
                        return;
                    }
                    return;
                }
                BluetoothDevice bluetoothDevice2 = (BluetoothDevice) intent.getParcelableExtra("android.bluetooth.device.extra.DEVICE");
                Parcelable[] parcelableArrayExtra = intent.getParcelableArrayExtra("android.bluetooth.device.extra.UUID");
                UUID[] uuidArr = parcelableArrayExtra == null ? null : new UUID[parcelableArrayExtra.length];
                if (uuidArr != null) {
                    for (int i = 0; i < parcelableArrayExtra.length; i++) {
                        uuidArr[i] = ((ParcelUuid) parcelableArrayExtra[i]).getUuid();
                    }
                }
                BluetoothClassic.this.mScanThread.pushUuid(bluetoothDevice2, uuidArr);
                return;
            }
            if (action.equals(BluetoothClassic.PERMISSION_GRANTED)) {
                Logger.m967d(BluetoothClassic.TAG, "Bluetooth Permission Guaranteed.");
                if (BluetoothClassic.this.mBluetoothAdapter.isEnabled()) {
                    Logger.m967d(BluetoothClassic.TAG, "Activated Bluetooth.");
                    BluetoothClassic.this.mDeviceState = DeviceState.ACTIVATED;
                    return;
                } else {
                    Logger.m967d(BluetoothClassic.TAG, "Activate Bluetooth.");
                    BluetoothClassic.this.mDeviceState = DeviceState.INACTIVATED;
                    BluetoothClassic.this.enableBluetooth();
                    return;
                }
            }
            if (action.equals(BluetoothClassic.PERMISSION_DENIED)) {
                Logger.m967d(BluetoothClassic.TAG, "Bluetooth Permission Denied.");
                BluetoothClassic.this.mDeviceState = DeviceState.INACTIVATED;
            } else if (action.equals(BluetoothClassic.PERMISSION_EXPLANATION_REQUIERED)) {
                Logger.m967d(BluetoothClassic.TAG, "Bluetooth Permission Explanation Required.");
                BluetoothClassic.this.requestPermissionExplanation();
            } else if (action.equals(BluetoothClassic.PERMISSION_REQUEST)) {
                Logger.m967d(BluetoothClassic.TAG, "Bluetooth Permission Requested.");
                BluetoothClassic.this.requestPermission();
            }
        }
    }

    private class ScanThread extends Thread {
        private final AtomicBoolean mExit = new AtomicBoolean(false);
        private final Set<BluetoothDevice> mFoundDevices = new HashSet();
        private BluetoothDevice mFetchingDevice = null;
        private UuidInfo mFetchedUuidInfo = null;
        private final ScheduledExecutorService mService = Executors.newSingleThreadScheduledExecutor();
        private ScheduledFuture<?> mFuture = null;

        private class UuidInfo {
            private BluetoothDevice mDevice;
            private UUID[] mUuid;

            UuidInfo(BluetoothDevice bluetoothDevice, UUID[] uuidArr) {
                this.mDevice = bluetoothDevice;
                if (uuidArr == null || uuidArr.length == 0) {
                    this.mUuid = null;
                    return;
                }
                UUID[] uuidArr2 = new UUID[uuidArr.length];
                this.mUuid = uuidArr2;
                System.arraycopy(uuidArr, 0, uuidArr2, 0, uuidArr.length);
            }
        }

        public ScanThread() {
        }

        private boolean isMatch(UuidInfo uuidInfo) {
            if (uuidInfo != null && uuidInfo.mDevice != null && uuidInfo.mUuid != null) {
                boolean zIsEqual = false;
                boolean zIsEqual2 = false;
                for (UUID uuid : uuidInfo.mUuid) {
                    Logger.m967d(BluetoothClassic.TAG, "UUID: device = " + uuidInfo.mDevice.toString() + ", uuid = " + uuid.toString());
                    if (!zIsEqual) {
                        BluetoothClassic bluetoothClassic = BluetoothClassic.this;
                        zIsEqual = bluetoothClassic.isEqual(uuid, UUID.fromString(bluetoothClassic.mConfig.getControlConnectionUuid()));
                    }
                    if (!zIsEqual2) {
                        BluetoothClassic bluetoothClassic2 = BluetoothClassic.this;
                        zIsEqual2 = bluetoothClassic2.isEqual(uuid, UUID.fromString(bluetoothClassic2.mConfig.getDataConnectionUuid()));
                    }
                }
                if (zIsEqual && zIsEqual2) {
                    return true;
                }
            }
            return false;
        }

        /* JADX WARN: Code restructure failed: missing block: B:10:0x004d, code lost:
        
            wait(r5.this$0.mConfig.mScanWaitTimeoutMs);
         */
        /* JADX WARN: Code restructure failed: missing block: B:11:0x005b, code lost:
        
            r0 = r5.mFetchedUuidInfo;
         */
        /* JADX WARN: Code restructure failed: missing block: B:12:0x005d, code lost:
        
            if (r0 != null) goto L16;
         */
        /* JADX WARN: Code restructure failed: missing block: B:13:0x005f, code lost:
        
            jp.konami.Logger.m968e(jp.konami.peerlink.btc.BluetoothClassic.TAG, "Fetch UUID timed out.");
         */
        /* JADX WARN: Code restructure failed: missing block: B:17:0x006c, code lost:
        
            if (isMatch(r0) == false) goto L23;
         */
        /* JADX WARN: Code restructure failed: missing block: B:19:0x0074, code lost:
        
            if (r5.mFetchedUuidInfo.mDevice == null) goto L23;
         */
        /* JADX WARN: Code restructure failed: missing block: B:20:0x0076, code lost:
        
            r0 = r5.mFetchedUuidInfo.mDevice;
         */
        /* JADX WARN: Code restructure failed: missing block: B:22:0x007d, code lost:
        
            return r0;
         */
        /* JADX WARN: Code restructure failed: missing block: B:9:0x0022, code lost:
        
            jp.konami.Logger.m967d(jp.konami.peerlink.btc.BluetoothClassic.TAG, "Fetching UUID. (device = " + r1.toString() + ")");
            r5.mFetchingDevice = r1;
            r5.mFetchedUuidInfo = null;
            r5.mFoundDevices.remove(r1);
         */
        /*
            Code decompiled incorrectly, please refer to instructions dump.
        */
        private BluetoothDevice popScanDevice() {
            loop0: while (true) {
                synchronized (this) {
                    Iterator<BluetoothDevice> it = this.mFoundDevices.iterator();
                    while (true) {
                        if (it.hasNext()) {
                            BluetoothDevice next = it.next();
                            if (next.fetchUuidsWithSdp()) {
                                break;
                            }
                            Logger.m968e(BluetoothClassic.TAG, "Failed to fetchUuidsWithSdp()");
                        }
                    }
                }
            }
            return null;
        }

        private boolean scan() {
            if (BluetoothClassic.this.mBluetoothAdapter.isDiscovering()) {
                Logger.m968e(BluetoothClassic.TAG, "Can not scan in discovering.");
                return false;
            }
            while (!this.mExit.get()) {
                BluetoothDevice bluetoothDevicePopScanDevice = popScanDevice();
                if (bluetoothDevicePopScanDevice == null) {
                    Logger.m967d(BluetoothClassic.TAG, "Finished scan.");
                    return true;
                }
                if (!scan(bluetoothDevicePopScanDevice)) {
                    Logger.m968e(BluetoothClassic.TAG, "Failed to scan.");
                }
            }
            return true;
        }

        private boolean scan(BluetoothDevice bluetoothDevice) {
            boolean z = false;
            if (bluetoothDevice == null) {
                return false;
            }
            Logger.m967d(BluetoothClassic.TAG, "Try to scan. (device = " + bluetoothDevice.toString() + ")");
            synchronized (BluetoothClassic.this.mFoundNodes) {
                Iterator it = BluetoothClassic.this.mFoundNodes.iterator();
                while (it.hasNext()) {
                    BluetoothDevice device = ((DeviceInfo) it.next()).getDevice();
                    if (device != null && device.equals(bluetoothDevice)) {
                        Logger.m967d(BluetoothClassic.TAG, "Already scanned. (device = " + bluetoothDevice.toString() + ")");
                        return false;
                    }
                }
                BluetoothSocket bluetoothSocketCreateInsecureRfcommSocketToServiceRecord = null;
                try {
                    bluetoothSocketCreateInsecureRfcommSocketToServiceRecord = bluetoothDevice.createInsecureRfcommSocketToServiceRecord(UUID.fromString(BluetoothClassic.this.mConfig.getControlConnectionUuid()));
                    this.mFuture = this.mService.schedule(new Runnable(bluetoothSocketCreateInsecureRfcommSocketToServiceRecord) { // from class: jp.konami.peerlink.btc.BluetoothClassic.ScanThread.1Task
                        private BluetoothSocket mSocket;

                        {
                            this.mSocket = bluetoothSocketCreateInsecureRfcommSocketToServiceRecord;
                        }

                        @Override // java.lang.Runnable
                        public void run() {
                            try {
                                this.mSocket.close();
                            } catch (IOException e) {
                                Logger.m968e(BluetoothClassic.TAG, "Unknown error.");
                                e.printStackTrace();
                            }
                        }
                    }, 3000L, TimeUnit.MILLISECONDS);
                    bluetoothSocketCreateInsecureRfcommSocketToServiceRecord.connect();
                    if (this.mFuture.cancel(false)) {
                        DatagramBluetoothSocket datagramBluetoothSocket = BluetoothClassic.this.new DatagramBluetoothSocket(bluetoothSocketCreateInsecureRfcommSocketToServiceRecord);
                        Logger.m967d(BluetoothClassic.TAG, "Scanning for " + datagramBluetoothSocket.getRemoteDevice().toString());
                        DeviceInfo deviceInfoRecvAdvertise = BluetoothClassic.this.recvAdvertise(datagramBluetoothSocket);
                        if (deviceInfoRecvAdvertise != null) {
                            Logger.m967d(BluetoothClassic.TAG, "Scan succeeded: address = " + deviceInfoRecvAdvertise.getDevice().getAddress() + ", id = " + deviceInfoRecvAdvertise.getId() + ", attribute = " + (deviceInfoRecvAdvertise.getAttribute() == null ? "" : deviceInfoRecvAdvertise.getAttribute().toString()));
                            synchronized (BluetoothClassic.this.mFoundNodes) {
                                BluetoothClassic.this.mFoundNodes.add(deviceInfoRecvAdvertise);
                            }
                            z = true;
                        }
                    } else {
                        Logger.m968e(BluetoothClassic.TAG, "Unknown error.");
                    }
                } finally {
                    try {
                    } finally {
                    }
                }
                return z;
            }
        }

        public void cancel() {
            this.mExit.set(true);
            interrupt();
            try {
                join();
            } catch (InterruptedException e) {
                Logger.m968e(BluetoothClassic.TAG, "Unknown error.");
                e.printStackTrace();
            }
            this.mService.shutdownNow();
        }

        protected void finalize() {
            cancel();
        }

        public boolean pushFoundDevice(BluetoothDevice bluetoothDevice) {
            boolean zAdd;
            if (bluetoothDevice == null || getState() == Thread.State.RUNNABLE) {
                return false;
            }
            synchronized (this) {
                zAdd = this.mFoundDevices.add(bluetoothDevice);
            }
            return zAdd;
        }

        public boolean pushUuid(BluetoothDevice bluetoothDevice, UUID[] uuidArr) {
            synchronized (this) {
                BluetoothDevice bluetoothDevice2 = this.mFetchingDevice;
                if (bluetoothDevice2 == null) {
                    return false;
                }
                if (bluetoothDevice == null) {
                    Logger.m968e(BluetoothClassic.TAG, "Unknown error.");
                    return false;
                }
                if (bluetoothDevice2.equals(bluetoothDevice)) {
                    this.mFetchingDevice = null;
                    this.mFetchedUuidInfo = new UuidInfo(bluetoothDevice, uuidArr);
                    notifyAll();
                }
                return true;
            }
        }

        @Override // java.lang.Thread, java.lang.Runnable
        public void run() {
            scan();
            BluetoothClassic.this.mDiscoveryState = DiscoveryState.INACTIVATED;
        }
    }

    public BluetoothClassic(Config config, Activity activity) throws IllegalArgumentException {
        this.mDeviceState = DeviceState.UNSUPPORTED;
        Logger.m967d(TAG, "Constructor.");
        this.mConfig = config;
        this.mActivity = activity;
        if (!config.isValid() || this.mActivity == null) {
            Logger.m967d(TAG, "Invalid argument.");
            throw new IllegalArgumentException("Invalid argument.");
        }
        if (this.mBluetoothAdapter == null) {
            this.mDeviceState = DeviceState.UNSUPPORTED;
            return;
        }
        Logger.m967d(TAG, "new Receiver()");
        this.mReceiver = new Receiver();
        this.mDeviceState = DeviceState.ACTIVATING;
        checkPermission();
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void checkPermission() {
        Logger.m967d(TAG, "checkPermission()");
        if (this.mDeviceState != DeviceState.ACTIVATING) {
            return;
        }
        ArrayDeque arrayDeque = new ArrayDeque();
        Boolean bool = false;
        Logger.m967d(TAG, "Android SDK:" + Build.VERSION.SDK_INT);
        for (String str : BluetoothSwitch.BLUETOOTH_PERMISSIONS) {
            if (ActivityCompat.checkSelfPermission(this.mActivity, str) == -1) {
                Logger.m967d(TAG, "Check " + str + " : permission denied!");
                if (ActivityCompat.shouldShowRequestPermissionRationale(this.mActivity, str)) {
                    Logger.m967d("btc/BluetoothSwitch ", str + " priviledge UI requested!");
                    bool = true;
                }
                arrayDeque.add(str);
            } else {
                Logger.m967d(TAG, "Check " + str + " : permission granted!");
            }
        }
        if (arrayDeque.size() == 0) {
            this.mActivity.sendBroadcast(new Intent(PERMISSION_GRANTED));
        } else if (bool.booleanValue()) {
            this.mActivity.sendBroadcast(new Intent(PERMISSION_EXPLANATION_REQUIERED));
        } else {
            this.mActivity.sendBroadcast(new Intent(PERMISSION_REQUEST));
        }
    }

    private void dispExplanationDialog() {
        Resources resources = this.mActivity.getResources();
        final String string = resources.getString(resources.getIdentifier("BTPermissionString2", "string", this.mActivity.getPackageName()));
        Logger.m967d(TAG, "DispExplanationDialog");
        this.mActivity.runOnUiThread(new Runnable() { // from class: jp.konami.peerlink.btc.BluetoothClassic.1
            @Override // java.lang.Runnable
            public void run() {
                AlertDialog.Builder builder = new AlertDialog.Builder(BluetoothClassic.this.mActivity);
                builder.setMessage(string);
                builder.setCancelable(false);
                builder.setPositiveButton("OK", new DialogInterface.OnClickListener() { // from class: jp.konami.peerlink.btc.BluetoothClassic.1.1
                    @Override // android.content.DialogInterface.OnClickListener
                    public void onClick(DialogInterface dialogInterface, int i) {
                        Logger.m967d(BluetoothClassic.TAG, "finish DispExplanationDialog");
                        BluetoothClassic.this.mActivity.sendBroadcast(new Intent(BluetoothClassic.PERMISSION_REQUEST));
                        dialogInterface.dismiss();
                    }
                });
                builder.create().show();
            }
        });
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void enableBluetooth() {
        Logger.m967d(TAG, "enableBluetooth()");
        if (this.mDeviceState != DeviceState.INACTIVATED) {
            return;
        }
        Intent intent = new Intent(this.mActivity, (Class<?>) BluetoothSwitch.class);
        intent.putExtra("BLUETOOTH_SWITCH", 0);
        this.mActivity.startActivity(intent);
        this.mDeviceState = DeviceState.ACTIVATING;
    }

    /* JADX INFO: Access modifiers changed from: private */
    public boolean isEqual(UUID uuid, UUID uuid2) {
        if (uuid.equals(uuid2)) {
            return true;
        }
        ByteBuffer byteBufferAllocate = ByteBuffer.allocate(16);
        byteBufferAllocate.putLong(uuid.getMostSignificantBits());
        byteBufferAllocate.putLong(uuid.getLeastSignificantBits());
        byte[] bArrArray = byteBufferAllocate.array();
        for (int i = 0; i < bArrArray.length / 2; i++) {
            byte b = (byte) (bArrArray[i] ^ bArrArray[(bArrArray.length - i) - 1]);
            bArrArray[i] = b;
            int length = (bArrArray.length - i) - 1;
            bArrArray[length] = (byte) (b ^ bArrArray[length]);
            bArrArray[i] = (byte) (bArrArray[i] ^ bArrArray[(bArrArray.length - i) - 1]);
        }
        byteBufferAllocate.rewind();
        UUID uuid3 = new UUID(byteBufferAllocate.getLong(), byteBufferAllocate.getLong());
        if (!uuid3.equals(uuid2)) {
            return false;
        }
        Logger.m967d(TAG, "UUID reverse: " + uuid.toString() + " -> " + uuid3.toString());
        return true;
    }

    /* JADX INFO: Access modifiers changed from: private */
    /* JADX WARN: Code restructure failed: missing block: B:10:0x0023, code lost:
    
        return null;
     */
    /* JADX WARN: Code restructure failed: missing block: B:12:0x0028, code lost:
    
        if (r1.hasRemaining() != false) goto L14;
     */
    /* JADX WARN: Code restructure failed: missing block: B:13:0x002a, code lost:
    
        r3 = null;
     */
    /* JADX WARN: Code restructure failed: missing block: B:14:0x002c, code lost:
    
        r3 = new java.util.HashMap();
     */
    /* JADX WARN: Code restructure failed: missing block: B:15:0x0031, code lost:
    
        if (r3 == null) goto L20;
     */
    /* JADX WARN: Code restructure failed: missing block: B:16:0x0033, code lost:
    
        r4 = new org.json.JSONObject(new java.lang.String(r1.array(), r1.position(), r1.limit() - r1.position()));
        r1 = r4.keys();
     */
    /* JADX WARN: Code restructure failed: missing block: B:18:0x0056, code lost:
    
        if (r1.hasNext() == false) goto L48;
     */
    /* JADX WARN: Code restructure failed: missing block: B:19:0x0058, code lost:
    
        r5 = r1.next().toString();
        r3.put(r5, r4.getString(r5));
     */
    /* JADX WARN: Code restructure failed: missing block: B:21:0x0078, code lost:
    
        return new jp.konami.peerlink.btc.BluetoothClassic.DeviceInfo(r10.getRemoteDevice(), new java.lang.String(r2), r3, r0);
     */
    /* JADX WARN: Code restructure failed: missing block: B:8:0x000e, code lost:
    
        r1 = java.nio.ByteBuffer.wrap(r3);
        r2 = new byte[r1.get() & 255];
        r1.get(r2);
     */
    /* JADX WARN: Code restructure failed: missing block: B:9:0x0021, code lost:
    
        if (r1.hasArray() != false) goto L11;
     */
    /*
        Code decompiled incorrectly, please refer to instructions dump.
    */
    public DeviceInfo recvAdvertise(DatagramBluetoothSocket datagramBluetoothSocket) {
        try {
            long jCurrentTimeMillis = System.currentTimeMillis();
            while (true) {
                byte[] bArrRecv = datagramBluetoothSocket.recv();
                if (bArrRecv != null && bArrRecv.length != 0) {
                    try {
                        break;
                    } catch (JSONException e) {
                        e.printStackTrace();
                        return null;
                    }
                }
                if (!datagramBluetoothSocket.isConnected()) {
                    return null;
                }
                if (System.currentTimeMillis() - jCurrentTimeMillis >= this.mConfig.getAdvertiseTimeoutMs()) {
                    Logger.m968e(TAG, "Advertise timedout.");
                    return null;
                }
                Thread.sleep(this.mConfig.getAdvertiseTimeoutMs() < 100 ? this.mConfig.getAdvertiseTimeoutMs() : 100L);
            }
        } catch (InterruptedException e2) {
            e2.printStackTrace();
            return null;
        }
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void requestPermission() {
        Logger.m967d(TAG, "requestPermission()");
        if (this.mDeviceState != DeviceState.ACTIVATING) {
            return;
        }
        Intent intent = new Intent(this.mActivity, (Class<?>) BluetoothSwitch.class);
        intent.putExtra("BLUETOOTH_SWITCH", BluetoothSwitch.REQUEST_PERMISSIONS);
        this.mActivity.startActivity(intent);
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void requestPermissionExplanation() {
        dispExplanationDialog();
    }

    /* JADX INFO: Access modifiers changed from: private */
    public boolean sendAdvertise(DatagramBluetoothSocket datagramBluetoothSocket) {
        try {
            ByteBuffer byteBufferAllocate = ByteBuffer.allocate(1500);
            int length = this.mConfig.getId().length();
            if (length > 255) {
                Logger.m968e(TAG, "Unknown error.");
                return false;
            }
            byteBufferAllocate.put((byte) length);
            byteBufferAllocate.put(this.mConfig.getId().getBytes());
            Map<String, String> attribute = this.mConfig.getAttribute();
            if (attribute != null) {
                byteBufferAllocate.put(new JSONObject(attribute).toString().getBytes());
            }
            if (!byteBufferAllocate.hasArray()) {
                Logger.m968e(TAG, "Unknown error.");
                return false;
            }
            if (byteBufferAllocate.position() > 1500) {
                Logger.m968e(TAG, "Invalid advertise data.");
                return false;
            }
            if (datagramBluetoothSocket.send(Arrays.copyOfRange(byteBufferAllocate.array(), 0, byteBufferAllocate.position()))) {
                return true;
            }
            Logger.m968e(TAG, "Failed to send advertise.");
            return false;
        } catch (NullPointerException e) {
            e.printStackTrace();
            return false;
        }
    }

    private boolean startDiscoverableThread() {
        ListenThread listenThread;
        AdvertiseThread advertiseThread;
        ListenThread listenThread2;
        AdvertiseThread advertiseThread2 = this.mAdvertiseThread;
        if (advertiseThread2 != null && advertiseThread2.isAlive() && (listenThread2 = this.mListenThread) != null && listenThread2.isAlive()) {
            return false;
        }
        AdvertiseThread advertiseThread3 = null;
        try {
            advertiseThread = new AdvertiseThread();
            try {
                advertiseThread.start();
                listenThread = new ListenThread();
                try {
                    listenThread.start();
                } catch (IOException unused) {
                    advertiseThread3 = advertiseThread;
                    Logger.m968e(TAG, "Unknown error.");
                    advertiseThread = advertiseThread3;
                }
            } catch (IOException unused2) {
                listenThread = null;
            }
        } catch (IOException unused3) {
            listenThread = null;
        }
        this.mAdvertiseThread = advertiseThread;
        this.mListenThread = listenThread;
        return true;
    }

    /* JADX INFO: Access modifiers changed from: private */
    public boolean stopDiscoverableThread() {
        AdvertiseThread advertiseThread = this.mAdvertiseThread;
        if (advertiseThread == null && this.mListenThread == null) {
            return false;
        }
        if (advertiseThread != null) {
            advertiseThread.cancel();
            this.mAdvertiseThread = null;
        }
        ListenThread listenThread = this.mListenThread;
        if (listenThread == null) {
            return true;
        }
        listenThread.cancel();
        this.mListenThread = null;
        return true;
    }

    public DeviceInfo accept() {
        ListenThread listenThread = this.mListenThread;
        if (listenThread == null) {
            return null;
        }
        return listenThread.accept();
    }

    public boolean close(DeviceInfo deviceInfo) {
        boolean z = false;
        if (deviceInfo == null) {
            return false;
        }
        if (this.mConnectThread != null && deviceInfo.getDevice().equals(this.mConnectThread.mSocket.getRemoteDevice())) {
            this.mConnectThread.cancel();
            this.mConnectThread = null;
            z = true;
        }
        if (this.mConnectionThreadController == null || !deviceInfo.getDevice().equals(this.mConnectionThreadController.mSocket.getRemoteDevice())) {
            return z;
        }
        this.mConnectionThreadController.cancel();
        this.mConnectionThreadController = null;
        return true;
    }

    public boolean connect(DeviceInfo deviceInfo) {
        if (this.mConnectThread == null && this.mConnectionThreadController == null) {
            try {
                ConnectThread connectThread = new ConnectThread(deviceInfo.getDevice());
                this.mConnectThread = connectThread;
                connectThread.start();
                return true;
            } catch (IOException unused) {
                Logger.m968e(TAG, "Unknown error.");
            }
        }
        return false;
    }

    public void destruct() {
        ScanThread scanThread;
        Receiver receiver = this.mReceiver;
        if (receiver != null) {
            receiver.destruct();
            this.mReceiver = null;
        }
        if (!stopDiscoverableMode()) {
            AdvertiseThread advertiseThread = this.mAdvertiseThread;
            if (advertiseThread != null) {
                advertiseThread.cancel();
                this.mAdvertiseThread = null;
            }
            ListenThread listenThread = this.mListenThread;
            if (listenThread != null) {
                listenThread.cancel();
                this.mListenThread = null;
            }
        }
        if (!stopDiscovery() && (scanThread = this.mScanThread) != null) {
            scanThread.cancel();
            this.mScanThread = null;
        }
        ConnectThread connectThread = this.mConnectThread;
        if (connectThread != null) {
            connectThread.cancel();
            this.mConnectThread = null;
        }
        ConnectionThreadController connectionThreadController = this.mConnectionThreadController;
        if (connectionThreadController != null) {
            connectionThreadController.cancel();
            this.mConnectionThreadController = null;
        }
        if (this.mBluetoothAdapter != null) {
            if (this.mDeviceState != DeviceState.ACTIVATED) {
                Logger.m967d(TAG, "mDeviceState[" + this.mDeviceState + "] != DeviceState.ACTIVATED");
            } else if (this.mBluetoothAdapter.isDiscovering()) {
                this.mBluetoothAdapter.cancelDiscovery();
            }
            this.mBluetoothAdapter = null;
        }
        synchronized (this.mFoundNodes) {
            this.mFoundNodes.clear();
        }
        this.mDeviceState = DeviceState.UNSUPPORTED;
        this.mDiscoveryState = DiscoveryState.INACTIVATED;
        this.mDiscoverableState = DiscoverableState.INACTIVATED;
    }

    public ConnectionState getConnectionState(DeviceInfo deviceInfo) {
        if (deviceInfo == null) {
            return ConnectionState.CLOSED;
        }
        ConnectionThreadController connectionThreadController = this.mConnectionThreadController;
        if (connectionThreadController != null && connectionThreadController.isAlive() && deviceInfo.getDevice().equals(this.mConnectionThreadController.mSocket.getRemoteDevice())) {
            return ConnectionState.ESTABLISHED;
        }
        ConnectThread connectThread = this.mConnectThread;
        if (connectThread != null && connectThread.isAlive() && deviceInfo.getDevice().equals(this.mConnectThread.mSocket.getRemoteDevice())) {
            return ConnectionState.CONNECTING;
        }
        synchronized (this.mFoundNodes) {
            if (!this.mFoundNodes.contains(deviceInfo)) {
                return ConnectionState.CLOSED;
            }
            return ConnectionState.OPEN;
        }
    }

    public List<DeviceInfo> getDetectedDeviceInfoList() {
        ArrayList arrayList = new ArrayList();
        synchronized (this.mFoundNodes) {
            if (arrayList.addAll(this.mFoundNodes)) {
                return arrayList;
            }
            return null;
        }
    }

    public DeviceState getDeviceState() {
        return this.mDeviceState;
    }

    public DiscoverableState getDiscoverableState() {
        return this.mDiscoverableState;
    }

    public DiscoveryState getDiscoveryState() {
        return this.mDiscoveryState;
    }

    public byte[] recv(DeviceInfo deviceInfo) {
        byte[] bArr;
        ConnectionThreadController connectionThreadController = this.mConnectionThreadController;
        if (connectionThreadController == null || !connectionThreadController.isAlive() || deviceInfo == null || !deviceInfo.getDevice().equals(this.mConnectionThreadController.mSocket.getRemoteDevice())) {
            return null;
        }
        synchronized (this.mConnectionThreadController.mRecvQueue) {
            bArr = (byte[]) this.mConnectionThreadController.mRecvQueue.poll();
        }
        return bArr;
    }

    public boolean send(DeviceInfo deviceInfo, byte[] bArr) {
        ConnectionThreadController connectionThreadController = this.mConnectionThreadController;

## Match/result managed hits
managed-work/jadx/sources/jp/konami/ExternalStorage.java:116:    public static boolean onActivityResult(int i, int i2, Intent intent) {
managed-work/jadx/sources/jp/konami/ExternalStorage.java:159:        ((Activity) context).startActivityForResult(new Intent("android.intent.action.OPEN_DOCUMENT_TREE"), DIR_PICKER_REQUEST_CODE);
managed-work/jadx/sources/jp/konami/ExternalStorage.java:170:        ((Activity) context).startActivityForResult(intent, FILE_PICKER_REQUEST_CODE);
managed-work/jadx/sources/jp/konami/android/common/FirebaseMessagingServiceDerived.java:121:                    String result = task.getResult();
managed-work/jadx/sources/jp/konami/android/common/FirebaseMessagingServiceDerived.java:122:                    FirebaseMessagingServiceDerived.s_fcmToken.set(result);
managed-work/jadx/sources/jp/konami/android/common/FirebaseMessagingServiceDerived.java:123:                    FirebaseImplementation.LogD("FcmToken / FcmToken = " + result);
managed-work/jadx/sources/jp/konami/android/common/FirebaseMessagingServiceDerived.java:125:                    FirebaseImplementation.LogW("FcmToken / Failed to task.getResult(). Exception message = " + e.getMessage());
managed-work/jadx/sources/com/epicgames/ue4/SplashActivity.java:237:    public void onRequestPermissionsResult(int i, String[] strArr, int[] iArr) {
managed-work/jadx/sources/com/epicgames/ue4/SplashActivity.java:285:                            SplashActivity.this.startActivityForResult(intent, 1);
managed-work/jadx/sources/com/epicgames/ue4/StoreHelper.java:19:    boolean onActivityResult(int i, int i2, Intent intent);
managed-work/jadx/sources/jp/konami/android/common/iab/OnAcknowledgeFinishedListener.java:3:import com.android.billingclient.api.BillingResult;
managed-work/jadx/sources/jp/konami/android/common/iab/OnAcknowledgeFinishedListener.java:7:    void onAcknowledgeFinished(BillingResult billingResult);
managed-work/jadx/sources/jp/konami/android/common/iab/OnShowInAppMessageFinishedListener.java:3:import com.android.billingclient.api.InAppMessageResult;
managed-work/jadx/sources/jp/konami/android/common/iab/OnShowInAppMessageFinishedListener.java:7:    void onShowInAppMessageFinished(InAppMessageResult inAppMessageResult);
managed-work/jadx/sources/com/epicgames/ue4/WebViewControl.java:21:import android.webkit.JsPromptResult;
managed-work/jadx/sources/com/epicgames/ue4/WebViewControl.java:22:import android.webkit.JsResult;
managed-work/jadx/sources/com/epicgames/ue4/WebViewControl.java:719:        public native boolean onJsAlert(WebView webView, String str, String str2, JsResult jsResult);
managed-work/jadx/sources/com/epicgames/ue4/WebViewControl.java:722:        public native boolean onJsBeforeUnload(WebView webView, String str, String str2, JsResult jsResult);
managed-work/jadx/sources/com/epicgames/ue4/WebViewControl.java:725:        public native boolean onJsConfirm(WebView webView, String str, String str2, JsResult jsResult);
managed-work/jadx/sources/com/epicgames/ue4/WebViewControl.java:728:        public native boolean onJsPrompt(WebView webView, String str, String str2, String str3, JsPromptResult jsPromptResult);
managed-work/jadx/sources/jp/konami/android/common/iab/OnGetItemDetailsFinishedListener.java:3:import com.android.billingclient.api.BillingResult;
managed-work/jadx/sources/jp/konami/android/common/iab/OnGetItemDetailsFinishedListener.java:9:    void onGetItemDetailsFinished(BillingResult billingResult, List<SkuDetails> list);
managed-work/jadx/sources/jp/konami/android/common/iab/OnConsumeFinishedListener.java:3:import com.android.billingclient.api.BillingResult;
managed-work/jadx/sources/jp/konami/android/common/iab/OnConsumeFinishedListener.java:8:    void onConsumeFinished(BillingResult billingResult, Purchase purchase);
managed-work/jadx/sources/jp/konami/android/common/iab/OnBillingProgramAvailabilityResponseFinishedListener.java:4:import com.android.billingclient.api.BillingResult;
managed-work/jadx/sources/jp/konami/android/common/iab/OnBillingProgramAvailabilityResponseFinishedListener.java:8:    void onBillingProgramAvailabilityResponseFinished(BillingResult billingResult, BillingProgramAvailabilityDetails billingProgramAvailabilityDetails);
managed-work/jadx/sources/jp/konami/android/common/iab/OnGetExternalTransactionTokenFinishedListener.java:3:import com.android.billingclient.api.BillingResult;
managed-work/jadx/sources/jp/konami/android/common/iab/OnGetExternalTransactionTokenFinishedListener.java:7:    void onGetExternalTransactionTokenFinished(BillingResult billingResult, String str);
managed-work/jadx/sources/jp/konami/pesam/C2396R.java:898:        public static final int textAppearanceSearchResultSubtitle = 2130903300;
managed-work/jadx/sources/jp/konami/pesam/C2396R.java:901:        public static final int textAppearanceSearchResultTitle = 2130903301;
managed-work/jadx/sources/jp/konami/pesam/C2396R.java:3321:        public static final int Base_TextAppearance_AppCompat_SearchResult = 2131689502;
managed-work/jadx/sources/jp/konami/pesam/C2396R.java:3324:        public static final int Base_TextAppearance_AppCompat_SearchResult_Subtitle = 2131689503;
managed-work/jadx/sources/jp/konami/pesam/C2396R.java:3327:        public static final int Base_TextAppearance_AppCompat_SearchResult_Title = 2131689504;
managed-work/jadx/sources/jp/konami/pesam/C2396R.java:3834:        public static final int TextAppearance_AppCompat_Light_SearchResult_Subtitle = 2131689678;
managed-work/jadx/sources/jp/konami/pesam/C2396R.java:3837:        public static final int TextAppearance_AppCompat_Light_SearchResult_Title = 2131689679;
managed-work/jadx/sources/jp/konami/pesam/C2396R.java:3855:        public static final int TextAppearance_AppCompat_SearchResult_Subtitle = 2131689685;
managed-work/jadx/sources/jp/konami/pesam/C2396R.java:3858:        public static final int TextAppearance_AppCompat_SearchResult_Title = 2131689686;
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabBaseNativeActivity.java:5:import com.android.billingclient.api.BillingResult;
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabBaseNativeActivity.java:6:import com.android.billingclient.api.InAppMessageResult;
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabBaseNativeActivity.java:30:            public void onAcknowledgeFinished(BillingResult billingResult) {
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabBaseNativeActivity.java:31:                KonamiIabBaseNativeActivity.this.nativeOnAcknowledgeFinished(billingResult);
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabBaseNativeActivity.java:46:        nativeOnBuyFinished(BillingResult.newBuilder().setResponseCode(5).build(), null);
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabBaseNativeActivity.java:56:        nativeOnBuyFinished(BillingResult.newBuilder().setResponseCode(5).build(), null);
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabBaseNativeActivity.java:74:                    public void onConsumeFinished(BillingResult billingResult, Purchase purchase2) {
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabBaseNativeActivity.java:75:                        KonamiIabBaseNativeActivity.this.nativeOnConsumeFinished(billingResult, purchase2);
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabBaseNativeActivity.java:89:            public void onGetBillingConfigFinished(BillingResult billingResult, BillingConfig billingConfig) {
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabBaseNativeActivity.java:90:                KonamiIabBaseNativeActivity.this.nativeOnGetBillingConfigFinished(billingResult, billingConfig);
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabBaseNativeActivity.java:118:                    public void onGetInventoryFinished(BillingResult billingResult, List<Purchase> list) {
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabBaseNativeActivity.java:119:                        KonamiIabBaseNativeActivity.this.nativeOnGetInventoryFinished(billingResult, list);
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabBaseNativeActivity.java:133:                    public void onGetItemProductDetailsFinished(BillingResult billingResult, List<ProductDetails> list) {
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabBaseNativeActivity.java:134:                        if (billingResult.getResponseCode() != 0 || list == null) {
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabBaseNativeActivity.java:135:                            Logger.m972w(KonamiIabBaseNativeActivity.TAG, "getItemProductDetails Failed Result:" + billingResult.getResponseCode());
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabBaseNativeActivity.java:137:                            Logger.m967d(KonamiIabBaseNativeActivity.TAG, "ProductDetails respond OK: " + billingResult.getResponseCode());
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabBaseNativeActivity.java:143:                        KonamiIabBaseNativeActivity.this.nativeOnGetItemProductDetailsFinished(billingResult, list);
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabBaseNativeActivity.java:242:            public void onBuyFinished(final BillingResult billingResult, final Purchase purchase) {
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabBaseNativeActivity.java:246:                        KonamiIabBaseNativeActivity.this.nativeOnBuyFinished(billingResult, purchase);
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabBaseNativeActivity.java:261:            public void onBuyFinished(final BillingResult billingResult, final Purchase purchase) {
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabBaseNativeActivity.java:265:                        KonamiIabBaseNativeActivity.this.nativeOnBuyFinished(billingResult, purchase);
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabBaseNativeActivity.java:310:    public native void nativeOnAcknowledgeFinished(BillingResult billingResult);
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabBaseNativeActivity.java:312:    public native void nativeOnBuyFinished(BillingResult billingResult, Purchase purchase);
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabBaseNativeActivity.java:314:    public native void nativeOnConsumeFinished(BillingResult billingResult, Purchase purchase);
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabBaseNativeActivity.java:316:    public native void nativeOnGetBillingConfigFinished(BillingResult billingResult, BillingConfig billingConfig);
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabBaseNativeActivity.java:318:    public native void nativeOnGetInventoryFinished(BillingResult billingResult, List<Purchase> list);
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabBaseNativeActivity.java:320:    public native void nativeOnGetItemDetailsFinished(BillingResult billingResult, List<SkuDetails> list);
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabBaseNativeActivity.java:322:    public native void nativeOnGetItemProductDetailsFinished(BillingResult billingResult, List<ProductDetails> list);
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabBaseNativeActivity.java:324:    public native void nativeOnQueryPurchaseHistoryAsyncFinished(BillingResult billingResult, List<PurchaseHistoryRecord> list);
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabBaseNativeActivity.java:326:    public native void nativeOnShowInAppMessageFinished(InAppMessageResult inAppMessageResult);
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabBaseNativeActivity.java:335:            public void onShowInAppMessageFinished(InAppMessageResult inAppMessageResult) {
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabBaseNativeActivity.java:336:                KonamiIabBaseNativeActivity.this.nativeOnShowInAppMessageFinished(inAppMessageResult);
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabBaseNativeActivity.java:346:        nativeOnBuyFinished(BillingResult.newBuilder().setResponseCode(5).build(), null);
managed-work/jadx/sources/jp/konami/pesam/DownloaderActivity.java:58:        setResult(-1, this.OutputData);
managed-work/jadx/sources/jp/konami/pesam/DownloaderActivity.java:339:            setResult(-1, this.OutputData);
managed-work/jadx/sources/jp/konami/pesam/DownloaderActivity.java:363:        setResult(-1, this.OutputData);
managed-work/jadx/sources/jp/konami/pesam/DownloaderActivity.java:393:                    downloaderActivity2.setResult(-1, downloaderActivity2.OutputData);
managed-work/jadx/sources/jp/konami/pesam/DownloaderActivity.java:407:                            DownloaderActivity.this.setResult(-1, DownloaderActivity.this.OutputData);
managed-work/jadx/sources/jp/konami/android/common/iab/OnGetBillingConfigFinishedListener.java:4:import com.android.billingclient.api.BillingResult;
managed-work/jadx/sources/jp/konami/android/common/iab/OnGetBillingConfigFinishedListener.java:8:    void onGetBillingConfigFinished(BillingResult billingResult, BillingConfig billingConfig);
managed-work/jadx/sources/jp/konami/android/common/iab/OnLaunchExternalLinkResponseFinishedListener.java:3:import com.android.billingclient.api.BillingResult;
managed-work/jadx/sources/jp/konami/android/common/iab/OnLaunchExternalLinkResponseFinishedListener.java:7:    void onLaunchExternalLinkResponseFinished(BillingResult billingResult);
managed-work/jadx/sources/jp/konami/peerlink/btc/BluetoothSwitch.java:24:    protected void onActivityResult(int i, int i2, Intent intent) {
managed-work/jadx/sources/jp/konami/peerlink/btc/BluetoothSwitch.java:39:            startActivityForResult(new Intent("android.bluetooth.adapter.action.REQUEST_ENABLE"), intExtra);
managed-work/jadx/sources/jp/konami/peerlink/btc/BluetoothSwitch.java:50:            startActivityForResult(intent, intExtra);
managed-work/jadx/sources/jp/konami/peerlink/btc/BluetoothSwitch.java:79:    public void onRequestPermissionsResult(int i, String[] strArr, int[] iArr) {
managed-work/jadx/sources/jp/konami/peerlink/btc/BluetoothSwitch.java:80:        super.onRequestPermissionsResult(i, strArr, iArr);
managed-work/jadx/sources/jp/konami/peerlink/btc/BluetoothSwitch.java:83:            Logger.m967d(TAG, "onRequestPermissionsResult called [grantResults.length:" + iArr.length + "]");
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabClient.java:19:import com.android.billingclient.api.BillingResult;
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabClient.java:28:import com.android.billingclient.api.InAppMessageResult;
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabClient.java:39:import com.android.billingclient.api.QueryProductDetailsResult;
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabClient.java:68:    private BillingResult launchBillingFlow(BillingFlowParams billingFlowParams) {
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabClient.java:85:            public void onBillingSetupFinished(BillingResult billingResult) {
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabClient.java:89:                    konamiIabInitializationFinishedListener2.onInitializationFinished(billingResult.getResponseCode() == 0);
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabClient.java:102:            public void onAcknowledgePurchaseResponse(BillingResult billingResult) {
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabClient.java:103:                onAcknowledgeFinishedListener.onAcknowledgeFinished(billingResult);
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabClient.java:140:    BillingResult buyItem(SkuDetails skuDetails, String str, String str2) {
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabClient.java:162:            public void onConsumeResponse(BillingResult billingResult, String str) {
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabClient.java:163:                onConsumeFinishedListener.onConsumeFinished(billingResult, purchase);
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabClient.java:202:            public void onBillingConfigResponse(BillingResult billingResult, BillingConfig billingConfig) {
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabClient.java:203:                onGetBillingConfigFinishedListener.onGetBillingConfigFinished(billingResult, billingConfig);
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabClient.java:219:            public void onCreateBillingProgramReportingDetailsResponse(BillingResult billingResult, BillingProgramReportingDetails billingProgramReportingDetails) {
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabClient.java:220:                if (billingResult.getResponseCode() != 0 || billingProgramReportingDetails == null) {
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabClient.java:221:                    onGetExternalTransactionTokenFinishedListener.onGetExternalTransactionTokenFinished(billingResult, null);
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabClient.java:223:                    onGetExternalTransactionTokenFinishedListener.onGetExternalTransactionTokenFinished(billingResult, billingProgramReportingDetails.getExternalTransactionToken());
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabClient.java:233:            public void onQueryPurchasesResponse(BillingResult billingResult, List<Purchase> list) {
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabClient.java:234:                onGetInventoryFinishedListener.onGetInventoryFinished(billingResult, list);
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabClient.java:248:            public void onProductDetailsResponse(BillingResult billingResult, QueryProductDetailsResult queryProductDetailsResult) {
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabClient.java:249:                onGetItemProductDetailsFinishedListener.onGetItemProductDetailsFinished(billingResult, queryProductDetailsResult.getProductDetailsList());
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabClient.java:298:            public void onPurchasesUpdated(BillingResult billingResult, List<Purchase> list) {
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabClient.java:300:                    onBuyFinishedListener.onBuyFinished(billingResult, null);
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabClient.java:304:                    if (KonamiIabClient.isAcknowledgeOnPurchase.booleanValue() && billingResult.getResponseCode() == 0 && !purchase.isAcknowledged() && purchase.getPurchaseState() == 1) {
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabClient.java:307:                            public void onAcknowledgeFinished(BillingResult billingResult2) {
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabClient.java:308:                                onBuyFinishedListener.onBuyFinished(billingResult2, purchase);
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabClient.java:312:                        onBuyFinishedListener.onBuyFinished(billingResult, purchase);
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabClient.java:325:            public void onBillingProgramAvailabilityResponse(BillingResult billingResult, BillingProgramAvailabilityDetails billingProgramAvailabilityDetails) {
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabClient.java:326:                onBillingProgramAvailabilityResponseFinishedListener.onBillingProgramAvailabilityResponseFinished(billingResult, billingProgramAvailabilityDetails);
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabClient.java:334:            public void onPurchasesUpdated(BillingResult billingResult, List<Purchase> list) {
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabClient.java:336:                    onBuyFinishedListener.onBuyFinished(billingResult, null);
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabClient.java:340:                    if (KonamiIabClient.isAcknowledgeOnPurchase.booleanValue() && billingResult.getResponseCode() == 0 && !purchase.isAcknowledged() && purchase.getPurchaseState() == 1) {
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabClient.java:343:                            public void onAcknowledgeFinished(BillingResult billingResult2) {
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabClient.java:344:                                onBuyFinishedListener.onBuyFinished(billingResult2, purchase);
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabClient.java:348:                        onBuyFinishedListener.onBuyFinished(billingResult, purchase);
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabClient.java:371:            public void onBillingProgramAvailabilityResponse(BillingResult billingResult, BillingProgramAvailabilityDetails billingProgramAvailabilityDetails) {
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabClient.java:372:                onBillingProgramAvailabilityResponseFinishedListener.onBillingProgramAvailabilityResponseFinished(billingResult, billingProgramAvailabilityDetails);
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabClient.java:408:            public void onLaunchExternalLinkResponse(BillingResult billingResult) {
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabClient.java:409:                onLaunchExternalLinkResponseFinishedListener.onLaunchExternalLinkResponseFinished(billingResult);
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabClient.java:424:    public BillingResult showInAppMessages(final OnShowInAppMessageFinishedListener onShowInAppMessageFinishedListener) {
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabClient.java:427:            public void onInAppMessageResponse(InAppMessageResult inAppMessageResult) {
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabClient.java:428:                onShowInAppMessageFinishedListener.onShowInAppMessageFinished(inAppMessageResult);
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabClient.java:433:    BillingResult upgradeSubscription(ProductDetails productDetails, String str, String str2, int i) {
managed-work/jadx/sources/jp/konami/android/common/iab/KonamiIabClient.java:438:    BillingResult upgradeSubscription(ProductDetails productDetails, String str, String str2, String str3, int i) {
managed-work/jadx/sources/jp/konami/android/common/iab/OnGetItemProductDetailsFinishedListener.java:3:import com.android.billingclient.api.BillingResult;
managed-work/jadx/sources/jp/konami/android/common/iab/OnGetItemProductDetailsFinishedListener.java:9:    void onGetItemProductDetailsFinished(BillingResult billingResult, List<ProductDetails> list);
managed-work/jadx/sources/jp/konami/android/common/iab/OnBuyFinishedListener.java:3:import com.android.billingclient.api.BillingResult;
managed-work/jadx/sources/jp/konami/android/common/iab/OnBuyFinishedListener.java:8:    void onBuyFinished(BillingResult billingResult, Purchase purchase);
managed-work/jadx/sources/jp/konami/android/common/iab/OnQueryPurchaseHistoryAsyncFinishedListener.java:3:import com.android.billingclient.api.BillingResult;
managed-work/jadx/sources/jp/konami/android/common/iab/OnQueryPurchaseHistoryAsyncFinishedListener.java:9:    void onQueryPurchaseHistoryAsyncFinished(BillingResult billingResult, List<PurchaseHistoryRecord> list);
managed-work/jadx/sources/jp/konami/android/common/iab/OnGetInventoryFinishedListener.java:3:import com.android.billingclient.api.BillingResult;
managed-work/jadx/sources/jp/konami/android/common/iab/OnGetInventoryFinishedListener.java:9:    void onGetInventoryFinished(BillingResult billingResult, List<Purchase> list);
managed-work/jadx/sources/jp/konami/android/common/Achievements.java:72:                    activity.startActivityForResult(intent, 4000);
managed-work/jadx/sources/jp/konami/android/common/GoogleImplementation.java:5:import com.google.android.gms.games.AuthenticationResult;
managed-work/jadx/sources/jp/konami/android/common/GoogleImplementation.java:85:        s_playerId = ((Player) task.getResult()).getPlayerId();
managed-work/jadx/sources/jp/konami/android/common/GoogleImplementation.java:146:    public static void updatePlayerId(Task<AuthenticationResult> task) {
managed-work/jadx/sources/jp/konami/android/common/GoogleImplementation.java:147:        boolean z = task.isSuccessful() && task.getResult().isAuthenticated();
managed-work/jadx/sources/jp/konami/peerlink/ble/BluetoothSwitch.java:22:    protected void onActivityResult(int i, int i2, Intent intent) {
managed-work/jadx/sources/jp/konami/peerlink/ble/BluetoothSwitch.java:34:            startActivityForResult(new Intent("android.bluetooth.adapter.action.REQUEST_ENABLE"), intExtra);
managed-work/jadx/sources/jp/konami/peerlink/ble/BluetoothSwitch.java:89:    public void onRequestPermissionsResult(int i, String[] strArr, int[] iArr) {
managed-work/jadx/sources/jp/konami/ExpansionDownloader/DownloaderManager.java:148:            ((Activity) context).startActivityForResult(new Intent(context, (Class<?>) DownloaderActivity.class), DownloadRequestCode);
managed-work/jadx/sources/jp/konami/ExpansionDownloader/DownloaderManager.java:235:    public static boolean onActivityResult(int i) {
managed-work/jadx/sources/jp/konami/android/common/Applilink.java:93:    public static void onActivityResult(int i, int i2, Intent intent) {
managed-work/jadx/sources/jp/konami/android/common/Applilink.java:94:        ApplilinkNetwork.handleActivityResult(i, i2, intent);
managed-work/jadx/sources/jp/konami/android/common/Applilink.java:340:        RecommendNetwork.openInterstitial(activity, "ADL_RESULT", new Point(i, i2), i3, ApplilinkConsts.AdVerticalAlign.TOP, new ApplilinkWebViewListener3() { // from class: jp.konami.android.common.Applilink.6
managed-work/jadx/sources/jp/konami/android/common/Applilink.java:531:        RecommendNetwork.getUnreadCount(ApplilinkConsts.AdModel.INTERSTITIAL, "ADL_RESULT", new ApplilinkNetworkHandler() { // from class: jp.konami.android.common.Applilink.12
managed-work/jadx/sources/jp/konami/AdMobReward.java:92:    private static int GOOGLE_CMP_PURPOSE_RESULT_OK = 0;
managed-work/jadx/sources/jp/konami/AdMobReward.java:93:    private static int GOOGLE_CMP_PURPOSE_RESULT_STRING_ERROR = 1;
managed-work/jadx/sources/jp/konami/AdMobReward.java:94:    private static int GOOGLE_CMP_PURPOSE_RESULT_DISAGREE = 2;
managed-work/jadx/sources/jp/konami/AdMobReward.java:95:    private static int GOOGLE_CMP_PURPOSE_RESULT_NONPARSONALIZE = 3;
managed-work/jadx/sources/jp/konami/AdMobReward.java:183:            Logger.m967d("eFootball_CMP_CheckGoogleCMPPurposeString", "GOOGLE_CMP_PURPOSE_RESULT_STRING_ERROR");
managed-work/jadx/sources/jp/konami/AdMobReward.java:184:            return GOOGLE_CMP_PURPOSE_RESULT_STRING_ERROR;
managed-work/jadx/sources/jp/konami/AdMobReward.java:187:            Logger.m967d("eFootball_CMP_CheckGoogleCMPPurposeString", "GOOGLE_CMP_PURPOSE_RESULT_DISAGREE");
managed-work/jadx/sources/jp/konami/AdMobReward.java:188:            return GOOGLE_CMP_PURPOSE_RESULT_DISAGREE;
managed-work/jadx/sources/jp/konami/AdMobReward.java:191:            return GOOGLE_CMP_PURPOSE_RESULT_OK;
managed-work/jadx/sources/jp/konami/AdMobReward.java:193:        Logger.m967d("eFootball_CMP_CheckGoogleCMPPurposeString", "GOOGLE_CMP_PURPOSE_RESULT_NONPARSONALIZE");
managed-work/jadx/sources/jp/konami/AdMobReward.java:194:        return GOOGLE_CMP_PURPOSE_RESULT_NONPARSONALIZE;
managed-work/jadx/sources/jp/konami/AdMobReward.java:318:            if (CheckGoogleCMPPurposeString(context) == GOOGLE_CMP_PURPOSE_RESULT_OK) {
managed-work/jadx/sources/jp/konami/AdMobReward.java:351:            ApplilinkSettings.forceOptOutInApp(iCheckGoogleCMPPurposeString != GOOGLE_CMP_PURPOSE_RESULT_OK);
managed-work/jadx/sources/jp/konami/AdMobReward.java:352:            if (iCheckGoogleCMPPurposeString == GOOGLE_CMP_PURPOSE_RESULT_STRING_ERROR) {
managed-work/jadx/sources/jp/konami/AdMobReward.java:359:            if (iCheckGoogleCMPPurposeString == GOOGLE_CMP_PURPOSE_RESULT_DISAGREE) {
managed-work/jadx/sources/jp/konami/AdMobReward.java:366:            if (iCheckGoogleCMPPurposeString == GOOGLE_CMP_PURPOSE_RESULT_NONPARSONALIZE) {
managed-work/jadx/sources/jp/konami/PermissionRequest.java:19:    private static boolean PermResult = false;
managed-work/jadx/sources/jp/konami/PermissionRequest.java:114:                if (z && !PermResult) {
managed-work/jadx/sources/jp/konami/PermissionRequest.java:183:            ((Activity) context).startActivityForResult(intent, PermRequestCode);
managed-work/jadx/sources/jp/konami/PermissionRequest.java:187:            ((Activity) context).startActivityForResult(intent2, PermRequestCode);
managed-work/jadx/sources/jp/konami/PermissionRequest.java:191:    public static boolean onActivityResult(int i) {
managed-work/jadx/sources/jp/konami/PermissionRequest.java:199:    public static void onRequestPermissionsResult(int i, int[] iArr) {
managed-work/jadx/sources/jp/konami/PermissionRequest.java:203:        PermResult = true;
managed-work/jadx/sources/jp/konami/PermissionRequest.java:210:                PermResult = false;
managed-work/jadx/sources/jp/konami/peerlink/ble/Central.java:14:import android.bluetooth.le.ScanResult;
managed-work/jadx/sources/jp/konami/peerlink/ble/Central.java:1443:            public void onBatchScanResults(List<ScanResult> list) {
managed-work/jadx/sources/jp/konami/peerlink/ble/Central.java:1444:                Iterator<ScanResult> it = list.iterator();
managed-work/jadx/sources/jp/konami/peerlink/ble/Central.java:1446:                    Logger.m967d(Central.TAG, "BatchScanResults: result = " + it.next().toString());
managed-work/jadx/sources/jp/konami/peerlink/ble/Central.java:1457:            public void onScanResult(int i, ScanResult scanResult) {
managed-work/jadx/sources/jp/konami/peerlink/ble/Central.java:1458:                Logger.m967d(Central.TAG, "ScanResult: callbackType = " + i + ", result = " + scanResult.toString());
managed-work/jadx/sources/jp/konami/peerlink/ble/Central.java:1459:                BluetoothDevice device = scanResult.getDevice();
managed-work/jadx/sources/jp/konami/peerlink/ble/Central.java:1463:                Iterator<ParcelUuid> it = scanResult.getScanRecord().getServiceUuids().iterator();
managed-work/jadx/sources/com/epicgames/ue4/BootCompleteReceiver.java:19:        private BroadcastReceiver.PendingResult pendingResult;
managed-work/jadx/sources/com/epicgames/ue4/BootCompleteReceiver.java:21:        Task(BroadcastReceiver.PendingResult pendingResult, Context context) {
managed-work/jadx/sources/com/epicgames/ue4/BootCompleteReceiver.java:22:            this.pendingResult = pendingResult;
managed-work/jadx/sources/com/epicgames/ue4/BootCompleteReceiver.java:93:            this.pendingResult.finish();
managed-work/jadx/sources/com/epicgames/ue4/GooglePlayStoreHelper.java:10:import com.android.billingclient.api.BillingResult;
managed-work/jadx/sources/com/epicgames/ue4/GooglePlayStoreHelper.java:19:import com.android.billingclient.api.QueryProductDetailsResult;
managed-work/jadx/sources/com/epicgames/ue4/GooglePlayStoreHelper.java:53:        void launchForResult(PendingIntent pendingIntent, int i);
managed-work/jadx/sources/com/epicgames/ue4/GooglePlayStoreHelper.java:63:            public void onPurchasesUpdated(BillingResult billingResult, List<Purchase> list) {
managed-work/jadx/sources/com/epicgames/ue4/GooglePlayStoreHelper.java:64:                if (billingResult.getResponseCode() != 0 || list == null) {
managed-work/jadx/sources/com/epicgames/ue4/GooglePlayStoreHelper.java:65:                    GooglePlayStoreHelper.this.Log.debug("[GooglePlayStoreHelper] - GooglePlayStoreHelper::UserCancelled Purchase " + billingResult.getDebugMessage());
managed-work/jadx/sources/com/epicgames/ue4/GooglePlayStoreHelper.java:66:                    GooglePlayStoreHelper.this.nativePurchaseComplete(billingResult.getResponseCode(), "", "", "", "");
managed-work/jadx/sources/com/epicgames/ue4/GooglePlayStoreHelper.java:70:                        GooglePlayStoreHelper.this.onPurchaseResult(billingResult, it.next());
managed-work/jadx/sources/com/epicgames/ue4/GooglePlayStoreHelper.java:83:            public void onBillingSetupFinished(BillingResult billingResult) {
managed-work/jadx/sources/com/epicgames/ue4/GooglePlayStoreHelper.java:84:                int responseCode = billingResult.getResponseCode();
managed-work/jadx/sources/com/epicgames/ue4/GooglePlayStoreHelper.java:87:                    googlePlayStoreHelper.Log.debug("In-app billing NOT supported for " + GooglePlayStoreHelper.this.gameActivity.getPackageName() + " error " + billingResult.getResponseCode());
managed-work/jadx/sources/com/epicgames/ue4/GooglePlayStoreHelper.java:141:            public void onProductDetailsResponse(BillingResult billingResult, QueryProductDetailsResult queryProductDetailsResult) {
managed-work/jadx/sources/com/epicgames/ue4/GooglePlayStoreHelper.java:142:                List<ProductDetails> productDetailsList = queryProductDetailsResult.getProductDetailsList();
managed-work/jadx/sources/com/epicgames/ue4/GooglePlayStoreHelper.java:143:                int responseCode = billingResult.getResponseCode();
managed-work/jadx/sources/com/epicgames/ue4/GooglePlayStoreHelper.java:171:                    public void onConsumeResponse(BillingResult billingResult, String str2) {
managed-work/jadx/sources/com/epicgames/ue4/GooglePlayStoreHelper.java:172:                        int responseCode = billingResult.getResponseCode();
managed-work/jadx/sources/com/epicgames/ue4/GooglePlayStoreHelper.java:177:                            GooglePlayStoreHelper.this.Log.debug("[GooglePlayStoreHelper] - ConsumePurchase failed with error " + GooglePlayStoreHelper.this.TranslateServerResponseCode(billingResult.getResponseCode()));
managed-work/jadx/sources/com/epicgames/ue4/GooglePlayStoreHelper.java:235:            public void onProductDetailsResponse(BillingResult billingResult, QueryProductDetailsResult queryProductDetailsResult) {
managed-work/jadx/sources/com/epicgames/ue4/GooglePlayStoreHelper.java:239:                List<ProductDetails> productDetailsList = queryProductDetailsResult.getProductDetailsList();
managed-work/jadx/sources/com/epicgames/ue4/GooglePlayStoreHelper.java:241:                int responseCode = billingResult.getResponseCode();
managed-work/jadx/sources/com/epicgames/ue4/GooglePlayStoreHelper.java:346:                            public void onConsumeResponse(BillingResult billingResult, String str) {
managed-work/jadx/sources/com/epicgames/ue4/GooglePlayStoreHelper.java:347:                                int responseCode = billingResult.getResponseCode();
managed-work/jadx/sources/com/epicgames/ue4/GooglePlayStoreHelper.java:355:                                    GooglePlayStoreHelper.this.Log.debug("[GooglePlayStoreHelper] - GooglePlayStoreHelper::RestorePurchases - consumePurchase failed for " + purchase.getSkus().get(0) + " with error " + billingResult.getResponseCode());
managed-work/jadx/sources/com/epicgames/ue4/GooglePlayStoreHelper.java:357:                                    arrayList6.add(Integer.valueOf(billingResult.getResponseCode()));
managed-work/jadx/sources/com/epicgames/ue4/GooglePlayStoreHelper.java:406:    public boolean onActivityResult(int i, int i2, Intent intent) {
managed-work/jadx/sources/com/epicgames/ue4/GooglePlayStoreHelper.java:407:        this.Log.debug("[GooglePlayStoreHelper] - GooglePlayStoreHelper::onActivityResult unimplemented on BillingApiV2");
managed-work/jadx/sources/com/epicgames/ue4/GooglePlayStoreHelper.java:419:    public boolean onPurchaseResult(BillingResult billingResult, final Purchase purchase) {
managed-work/jadx/sources/com/epicgames/ue4/GooglePlayStoreHelper.java:420:        this.Log.debug("[GooglePlayStoreHelper] - GooglePlayStoreHelper::onPurchaseResult");
managed-work/jadx/sources/com/epicgames/ue4/GooglePlayStoreHelper.java:421:        if (billingResult == null) {
managed-work/jadx/sources/com/epicgames/ue4/GooglePlayStoreHelper.java:422:            this.Log.debug("Null data in purchase activity result.");
managed-work/jadx/sources/com/epicgames/ue4/GooglePlayStoreHelper.java:426:        int responseCode = billingResult.getResponseCode();
managed-work/jadx/sources/com/epicgames/ue4/GooglePlayStoreHelper.java:428:            this.Log.debug("[GooglePlayStoreHelper] - GooglePlayStoreHelper::onActivityResult - Processing purchase result. Response Code: " + TranslateServerResponseCode(responseCode));
managed-work/jadx/sources/com/epicgames/ue4/GooglePlayStoreHelper.java:445:                logger.debug("[GooglePlayStoreHelper] - GooglePlayStoreHelper::onActivityResult - Purchase canceled." + TranslateServerResponseCode(responseCode));
managed-work/jadx/sources/com/epicgames/ue4/GooglePlayStoreHelper.java:448:                logger.debug("[GooglePlayStoreHelper] - GooglePlayStoreHelper::onActivityResult - Purchase failed. Result code: " + Integer.toString(responseCode) + ". Response: " + TranslateServerResponseCode(responseCode));
managed-work/jadx/sources/com/epicgames/ue4/GameActivity.java:108:import com.google.android.gms.common.ConnectionResult;
managed-work/jadx/sources/com/epicgames/ue4/GameActivity.java:198:    public static final String DOWNLOAD_RETURN_NAME = "Result";
managed-work/jadx/sources/com/epicgames/ue4/GameActivity.java:291:    private int NumTimesScreenCaptureDisabled = 0;
managed-work/jadx/sources/com/epicgames/ue4/GameActivity.java:1013:    private void SetDisableScreenCaptureInternal(boolean z) {
managed-work/jadx/sources/com/epicgames/ue4/GameActivity.java:1018:                    GameActivity.Log.debug("==============> [JAVA] AndroidThunkJava_DisableScreenCapture(true) - Disabled screen captures");
managed-work/jadx/sources/com/epicgames/ue4/GameActivity.java:1026:                    GameActivity.Log.debug("==============> [JAVA] AndroidThunkJava_DisableScreenCapture(false) - Enabled screen captures");
managed-work/jadx/sources/com/epicgames/ue4/GameActivity.java:2457:    public void AndroidThunkJava_DisableScreenCapture(boolean z) {
managed-work/jadx/sources/com/epicgames/ue4/GameActivity.java:2458:        boolean zAndroidThunkJava_IsScreenCaptureDisabled = AndroidThunkJava_IsScreenCaptureDisabled();
managed-work/jadx/sources/com/epicgames/ue4/GameActivity.java:2459:        this.NumTimesScreenCaptureDisabled += z ? 1 : -1;
managed-work/jadx/sources/com/epicgames/ue4/GameActivity.java:2460:        if (AndroidThunkJava_IsScreenCaptureDisabled() != zAndroidThunkJava_IsScreenCaptureDisabled) {
managed-work/jadx/sources/com/epicgames/ue4/GameActivity.java:2461:            SetDisableScreenCaptureInternal(!zAndroidThunkJava_IsScreenCaptureDisabled);
managed-work/jadx/sources/com/epicgames/ue4/GameActivity.java:2925:    public boolean AndroidThunkJava_IsScreenCaptureDisabled() {
managed-work/jadx/sources/com/epicgames/ue4/GameActivity.java:2926:        return this.NumTimesScreenCaptureDisabled != 0;
managed-work/jadx/sources/com/epicgames/ue4/GameActivity.java:3590:    public native void nativeOnActivityResult(GameActivity gameActivity, int i, int i2, Intent intent);
managed-work/jadx/sources/com/epicgames/ue4/GameActivity.java:3628:    public native void nativeVirtualKeyboardResult(boolean z, String str);
managed-work/jadx/sources/com/epicgames/ue4/GameActivity.java:3645:    protected void onActivityResult(int i, int i2, Intent intent) {
managed-work/jadx/sources/com/epicgames/ue4/GameActivity.java:3648:        if (PermissionRequest.onActivityResult(i) || DownloaderManager.onActivityResult(i) || ExternalStorage.onActivityResult(i, i2, intent)) {
managed-work/jadx/sources/com/epicgames/ue4/GameActivity.java:3692:            super.onActivityResult(i, i2, intent);
managed-work/jadx/sources/com/epicgames/ue4/GameActivity.java:3695:            nativeOnActivityResult(this, i, i2, intent);
managed-work/jadx/sources/com/epicgames/ue4/GameActivity.java:3697:        Applilink.onActivityResult(i, i2, intent);
managed-work/jadx/sources/com/epicgames/ue4/GameActivity.java:3722:    public void onConnectionFailed(ConnectionResult connectionResult) {
managed-work/jadx/sources/com/epicgames/ue4/GameActivity.java:3723:        Log.debug("Google Client Connect failed. Error Code: " + connectionResult.getErrorCode() + " Description: " + connectionResult.getErrorMessage());
managed-work/jadx/sources/com/epicgames/ue4/GameActivity.java:4215:                    GameActivity.this.nativeVirtualKeyboardResult(true, GameActivity.this.virtualKeyboardInputBox.getText().toString());
managed-work/jadx/sources/com/epicgames/ue4/GameActivity.java:4225:                    GameActivity.this.nativeVirtualKeyboardResult(false, " ");
managed-work/jadx/sources/com/epicgames/ue4/GameActivity.java:4448:    public void onRequestPermissionsResult(int i, String[] strArr, int[] iArr) {
managed-work/jadx/sources/com/epicgames/ue4/GameActivity.java:4449:        super.onRequestPermissionsResult(i, strArr, iArr);
managed-work/jadx/sources/com/epicgames/ue4/GameActivity.java:4450:        PermissionRequest.onRequestPermissionsResult(i, iArr);
managed-work/jadx/sources/com/epicgames/ue4/GameActivity.java:4497:        SetDisableScreenCaptureInternal(AndroidThunkJava_IsScreenCaptureDisabled());
