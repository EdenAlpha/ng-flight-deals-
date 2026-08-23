package jp.konami.peerlink.wifidirect;

import android.app.Activity;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.net.wifi.p2p.WifiP2pConfig;
import android.net.wifi.p2p.WifiP2pDevice;
import android.net.wifi.p2p.WifiP2pInfo;
import android.net.wifi.p2p.WifiP2pManager;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.ScheduledFuture;
import java.util.concurrent.TimeUnit;
import java.util.regex.Pattern;
import jp.konami.Logger;
import jp.konami.peerlink.wifidirect.WifiDirectNsd;
import org.json.JSONException;
import org.json.JSONObject;

/* JADX INFO: loaded from: classes3.dex */
public class WifiDirect {
    private static final String ATTRIBUTE_KEY_ID = "id";
    private static final String ATTRIBUTE_KEY_PORT = "port";
    private static final String ATTRIBUTE_KEY_USER_ATTRIBUTE = "user_attribute";
    private static final int SELECT_TIMEOUT_MS = 100;
    private Activity mActivity;
    private WifiP2pManager.Channel mChannel;
    private Config mConfig;
    private DeviceState mDeviceState;
    private NetworkInfo mNetworkInfo;
    private Receiver mReceiver;
    private WifiDirectNsd mWifiDirectNsd;
    private WifiP2pManager mWifiP2pManager;

    public enum AdvertisementState {
        ACTIVATING,
        ACTIVATED,
        INACTIVATING,
        INACTIVATED
    }

    public static class Config {
        private Map mAttribute;
        private String mId;
        private int mPort = 0;
        private String mServiceId;

        /* JADX INFO: Access modifiers changed from: private */
        public boolean isValid() {
            String str;
            String str2 = this.mServiceId;
            return (str2 == null || str2.isEmpty() || (str = this.mId) == null || str.isEmpty() || this.mPort <= 0 || Pattern.compile("[^a-z0-9-]").matcher(this.mServiceId).find()) ? false : true;
        }

        public Map<String, String> getAttribute() {
            return this.mAttribute;
        }

        public String getId() {
            return this.mId;
        }

        public int getPort() {
            return this.mPort;
        }

        public String getServiceId() {
            return this.mServiceId;
        }

        public void setAttribute(String str, String str2) {
            if (this.mAttribute == null) {
                this.mAttribute = new HashMap();
            }
            this.mAttribute.put(str, str2);
        }

        public void setId(String str) {
            this.mId = str;
        }

        public void setPort(int i) {
            this.mPort = i;
        }

        public void setServiceId(String str) {
            this.mServiceId = str;
        }
    }

    public enum DeviceState {
        UNSUPPORTED,
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

    public static class NetworkInfo {
        private static final long DELAY_MS = 1000;
        private Config mConfig;
        private ConnectionState mConnectionState;
        private ScheduledFuture<?> mFuture;
        private ScheduledExecutorService mService;
        private ServiceInfo mServiceInfo;
        private WifiP2pInfo mWifiP2pInfo;

        public enum ConnectionState {
            OPEN,
            CREATING,
            CONNECTING,
            ESTABLISHED,
            CLOSED
        }

        private class Task implements Runnable {
            private Task() {
            }

            @Override // java.lang.Runnable
            public void run() {
                NetworkInfo.this.init();
            }
        }

        private NetworkInfo(Config config) {
            this.mConfig = null;
            this.mConnectionState = ConnectionState.OPEN;
            this.mServiceInfo = null;
            this.mWifiP2pInfo = null;
            this.mService = Executors.newSingleThreadScheduledExecutor();
            this.mFuture = null;
            this.mConfig = config;
            init();
        }

        /* JADX INFO: Access modifiers changed from: private */
        public synchronized void changeConnectionState(ConnectionState connectionState) {
            this.mConnectionState = connectionState;
        }

        /* JADX INFO: Access modifiers changed from: private */
        public synchronized void init() {
            this.mConnectionState = ConnectionState.OPEN;
            this.mServiceInfo = null;
            this.mWifiP2pInfo = null;
        }

        /* JADX INFO: Access modifiers changed from: private */
        public synchronized void set(WifiP2pInfo wifiP2pInfo) {
            this.mWifiP2pInfo = new WifiP2pInfo(wifiP2pInfo);
        }

        /* JADX INFO: Access modifiers changed from: private */
        public synchronized void set(ServiceInfo serviceInfo) {
            this.mServiceInfo = new ServiceInfo(serviceInfo);
        }

        /* JADX INFO: Access modifiers changed from: private */
        public void stopDelayDisconnect() {
            ScheduledFuture<?> scheduledFuture = this.mFuture;
            if (scheduledFuture != null) {
                scheduledFuture.cancel(true);
            }
        }

        /* JADX INFO: Access modifiers changed from: private */
        public synchronized boolean tryDelayDisconnect() {
            if (getConnectionState() == ConnectionState.ESTABLISHED && isGroupOwner()) {
                this.mFuture = this.mService.schedule(new Task(), 1000L, TimeUnit.MILLISECONDS);
                return true;
            }
            return false;
        }

        public synchronized ConnectionState getConnectionState() {
            return this.mConnectionState;
        }

        public synchronized Map<String, String> getGroupOwnerAttribute() {
            Map<String, String> attribute = null;
            if (!isGroupOwner()) {
                ServiceInfo serviceInfo = this.mServiceInfo;
                if (serviceInfo != null) {
                    attribute = serviceInfo.getAttribute();
                }
                return attribute;
            }
            Config config = this.mConfig;
            if (config == null) {
                return null;
            }
            return config.getAttribute();
        }

        public synchronized String getGroupOwnerHostName() {
            WifiP2pInfo wifiP2pInfo = this.mWifiP2pInfo;
            if (wifiP2pInfo != null && wifiP2pInfo.groupFormed) {
                return this.mWifiP2pInfo.groupOwnerAddress.getHostName();
            }
            return null;
        }

        public synchronized String getGroupOwnerId() {
            if (!isGroupOwner()) {
                ServiceInfo serviceInfo = this.mServiceInfo;
                return serviceInfo == null ? "" : serviceInfo.getId();
            }
            Config config = this.mConfig;
            if (config == null) {
                return "";
            }
            return config.getId();
        }

        public synchronized int getGroupOwnerPort() {
            int port = 0;
            if (!isGroupOwner()) {
                ServiceInfo serviceInfo = this.mServiceInfo;
                if (serviceInfo != null) {
                    port = serviceInfo.getPort();
                }
                return port;
            }
            Config config = this.mConfig;
            if (config == null) {
                return 0;
            }
            return config.getPort();
        }

        public synchronized boolean isGroupOwner() {
            WifiP2pInfo wifiP2pInfo = this.mWifiP2pInfo;
            if (wifiP2pInfo != null && wifiP2pInfo.groupFormed) {
                return this.mWifiP2pInfo.isGroupOwner;
            }
            return false;
        }
    }

    private class Receiver extends BroadcastReceiver {
        private boolean mRegistered;

        public Receiver() {
            this.mRegistered = false;
            IntentFilter intentFilter = new IntentFilter();
            intentFilter.addAction("android.net.wifi.p2p.STATE_CHANGED");
            intentFilter.addAction("android.net.wifi.p2p.CONNECTION_STATE_CHANGE");
            intentFilter.addAction("android.net.wifi.p2p.THIS_DEVICE_CHANGED");
            WifiDirect.this.mActivity.registerReceiver(this, intentFilter, 4);
            this.mRegistered = true;
        }

        public void destruct() {
            if (this.mRegistered) {
                this.mRegistered = false;
                WifiDirect.this.mActivity.unregisterReceiver(this);
            }
        }

        protected void finalize() {
            destruct();
        }

        @Override // android.content.BroadcastReceiver
        public void onReceive(Context context, Intent intent) {
            String action = intent.getAction();
            if (action.equals("android.net.wifi.p2p.STATE_CHANGED")) {
                int intExtra = intent.getIntExtra("wifi_p2p_state", -1);
                WifiDirect wifiDirect = WifiDirect.this;
                if (intExtra == 2) {
                    wifiDirect.mDeviceState = DeviceState.ACTIVATING;
                    Logger.m967d("WifiDirect", "Enabled WifiP2p.");
                    return;
                } else {
                    wifiDirect.mDeviceState = DeviceState.INACTIVATED;
                    Logger.m967d("WifiDirect", "Disabled WifiP2p.");
                    return;
                }
            }
            if (!action.equals("android.net.wifi.p2p.CONNECTION_STATE_CHANGE")) {
                if (action.equals("android.net.wifi.p2p.THIS_DEVICE_CHANGED")) {
                    Logger.m967d("WifiDirect", "Device changed: \n" + ((WifiP2pDevice) intent.getParcelableExtra("wifiP2pDevice")).toString());
                    return;
                }
                return;
            }
            android.net.NetworkInfo networkInfo = (android.net.NetworkInfo) intent.getParcelableExtra("networkInfo");
            if (WifiDirect.this.mDeviceState == DeviceState.ACTIVATING) {
                boolean zIsConnected = networkInfo.isConnected();
                WifiDirect wifiDirect2 = WifiDirect.this;
                if (zIsConnected) {
                    wifiDirect2.mWifiP2pManager.removeGroup(WifiDirect.this.mChannel, new WifiP2pManager.ActionListener() { // from class: jp.konami.peerlink.wifidirect.WifiDirect.Receiver.1
                        @Override // android.net.wifi.p2p.WifiP2pManager.ActionListener
                        public void onFailure(int i) {
                            Logger.m968e("WifiDirect", "Failed to removeGroup. (error = " + i + ")");
                        }

                        @Override // android.net.wifi.p2p.WifiP2pManager.ActionListener
                        public void onSuccess() {
                            Logger.m967d("WifiDirect", "Closed.");
                        }
                    });
                    return;
                } else {
                    wifiDirect2.mDeviceState = DeviceState.ACTIVATED;
                    return;
                }
            }
            Logger.m967d("WifiDirect", "Connection changed: \n" + networkInfo.toString());
            boolean zIsConnected2 = networkInfo.isConnected();
            WifiDirect wifiDirect3 = WifiDirect.this;
            if (!zIsConnected2) {
                if (wifiDirect3.mNetworkInfo.tryDelayDisconnect()) {
                    return;
                }
                WifiDirect.this.mNetworkInfo.init();
                return;
            }
            wifiDirect3.mNetworkInfo.stopDelayDisconnect();
            NetworkInfo.ConnectionState connectionState = WifiDirect.this.mNetworkInfo.getConnectionState();
            if (connectionState != NetworkInfo.ConnectionState.OPEN && connectionState != NetworkInfo.ConnectionState.CLOSED) {
                WifiDirect.this.mWifiP2pManager.requestConnectionInfo(WifiDirect.this.mChannel, new WifiP2pManager.ConnectionInfoListener() { // from class: jp.konami.peerlink.wifidirect.WifiDirect.Receiver.3
                    @Override // android.net.wifi.p2p.WifiP2pManager.ConnectionInfoListener
                    public void onConnectionInfoAvailable(WifiP2pInfo wifiP2pInfo) {
                        Logger.m967d("WifiDirect", "Connection info availed: \n" + wifiP2pInfo.toString());
                        NetworkInfo.ConnectionState connectionState2 = WifiDirect.this.mNetworkInfo.getConnectionState();
                        if (!(connectionState2 == NetworkInfo.ConnectionState.CREATING && wifiP2pInfo.isGroupOwner) && (!(connectionState2 == NetworkInfo.ConnectionState.ESTABLISHED && WifiDirect.this.mNetworkInfo.isGroupOwner() && wifiP2pInfo.isGroupOwner) && (connectionState2 != NetworkInfo.ConnectionState.CONNECTING || wifiP2pInfo.isGroupOwner))) {
                            Logger.m968e("WifiDirect", "Unknown error.");
                            WifiDirect.this.mWifiP2pManager.removeGroup(WifiDirect.this.mChannel, new WifiP2pManager.ActionListener() { // from class: jp.konami.peerlink.wifidirect.WifiDirect.Receiver.3.1
                                @Override // android.net.wifi.p2p.WifiP2pManager.ActionListener
                                public void onFailure(int i) {
                                    Logger.m968e("WifiDirect", "Failed to removeGroup. (error = " + i + ")");
                                }

                                @Override // android.net.wifi.p2p.WifiP2pManager.ActionListener
                                public void onSuccess() {
                                    Logger.m967d("WifiDirect", "Closed.");
                                }
                            });
                        } else {
                            WifiDirect.this.mNetworkInfo.set(wifiP2pInfo);
                            WifiDirect.this.mNetworkInfo.changeConnectionState(NetworkInfo.ConnectionState.ESTABLISHED);
                        }
                    }
                });
            } else {
                Logger.m968e("WifiDirect", "Unknown error.");
                WifiDirect.this.mWifiP2pManager.removeGroup(WifiDirect.this.mChannel, new WifiP2pManager.ActionListener() { // from class: jp.konami.peerlink.wifidirect.WifiDirect.Receiver.2
                    @Override // android.net.wifi.p2p.WifiP2pManager.ActionListener
                    public void onFailure(int i) {
                        Logger.m968e("WifiDirect", "Failed to removeGroup. (error = " + i + ")");
                    }

                    @Override // android.net.wifi.p2p.WifiP2pManager.ActionListener
                    public void onSuccess() {
                        Logger.m967d("WifiDirect", "Closed.");
                    }
                });
            }
        }
    }

    public static class ServiceInfo {
        private WifiDirectNsd.DetectedServiceInfo mDetectedServiceInfo;

        public ServiceInfo(ServiceInfo serviceInfo) {
            this(serviceInfo.mDetectedServiceInfo);
        }

        private ServiceInfo(WifiDirectNsd.DetectedServiceInfo detectedServiceInfo) {
            this.mDetectedServiceInfo = new WifiDirectNsd.DetectedServiceInfo(detectedServiceInfo);
        }

        /* JADX INFO: Access modifiers changed from: private */
        public WifiP2pDevice getDevice() {
            return this.mDetectedServiceInfo.getDevice();
        }

        public boolean equals(Object obj) {
            if (obj == null) {
                return false;
            }
            if (!(obj instanceof ServiceInfo)) {
                return super.equals(obj);
            }
            WifiDirectNsd.DetectedServiceInfo detectedServiceInfo = this.mDetectedServiceInfo;
            WifiDirectNsd.DetectedServiceInfo detectedServiceInfo2 = ((ServiceInfo) obj).mDetectedServiceInfo;
            return detectedServiceInfo == null ? detectedServiceInfo2 == null : detectedServiceInfo.equals(detectedServiceInfo2);
        }

        public Map<String, String> getAttribute() {
            String str;
            Map<String, String> attribute = this.mDetectedServiceInfo.getAttribute();
            if (attribute == null || (str = attribute.get(WifiDirect.ATTRIBUTE_KEY_USER_ATTRIBUTE)) == null) {
                return null;
            }
            try {
                JSONObject jSONObject = new JSONObject(str);
                Iterator<String> itKeys = jSONObject.keys();
                HashMap map = null;
                while (itKeys.hasNext()) {
                    if (map == null) {
                        map = new HashMap();
                    }
                    String string = itKeys.next().toString();
                    map.put(string, jSONObject.getString(string));
                }
                return map;
            } catch (JSONException e) {
                e.printStackTrace();
                return null;
            }
        }

        public String getId() {
            Map<String, String> attribute = this.mDetectedServiceInfo.getAttribute();
            return attribute == null ? "" : attribute.get(WifiDirect.ATTRIBUTE_KEY_ID);
        }

        public int getPort() {
            String str;
            Map<String, String> attribute = this.mDetectedServiceInfo.getAttribute();
            if (attribute == null || (str = attribute.get(WifiDirect.ATTRIBUTE_KEY_PORT)) == null) {
                return 0;
            }
            return Integer.valueOf(str).intValue();
        }

        public int hashCode() {
            return this.mDetectedServiceInfo.hashCode();
        }
    }

    public WifiDirect(Config config, Activity activity) throws IllegalArgumentException {
        this.mDeviceState = DeviceState.INACTIVATED;
        if (!config.isValid() || activity == null) {
            Logger.m967d("WifiDirect", "Invalid argument.");
            throw new IllegalArgumentException("Invalid argument.");
        }
        this.mDeviceState = DeviceState.ACTIVATING;
        WifiP2pManager wifiP2pManager = (WifiP2pManager) activity.getSystemService("wifip2p");
        if (wifiP2pManager == null) {
            this.mDeviceState = DeviceState.UNSUPPORTED;
            return;
        }
        this.mConfig = config;
        this.mActivity = activity;
        this.mWifiP2pManager = wifiP2pManager;
        this.mChannel = wifiP2pManager.initialize(activity, activity.getMainLooper(), new WifiP2pManager.ChannelListener() { // from class: jp.konami.peerlink.wifidirect.WifiDirect.1
            @Override // android.net.wifi.p2p.WifiP2pManager.ChannelListener
            public void onChannelDisconnected() {
                Logger.m967d("WifiDirect", "The channel has been disconnected.");
                WifiDirect.this.mDeviceState = DeviceState.INACTIVATED;
            }
        });
        this.mWifiDirectNsd = new WifiDirectNsd(this.mWifiP2pManager, this.mChannel);
        this.mNetworkInfo = new NetworkInfo(this.mConfig);
        this.mReceiver = new Receiver();
    }

    public boolean close() {
        if (this.mWifiP2pManager == null || this.mChannel == null || this.mDeviceState == DeviceState.UNSUPPORTED || this.mDeviceState == DeviceState.INACTIVATED || this.mNetworkInfo.getConnectionState() == NetworkInfo.ConnectionState.OPEN || this.mNetworkInfo.getConnectionState() == NetworkInfo.ConnectionState.CLOSED) {
            return false;
        }
        NetworkInfo.ConnectionState connectionState = this.mNetworkInfo.getConnectionState();
        NetworkInfo.ConnectionState connectionState2 = NetworkInfo.ConnectionState.CONNECTING;
        WifiP2pManager wifiP2pManager = this.mWifiP2pManager;
        if (connectionState == connectionState2) {
            wifiP2pManager.cancelConnect(this.mChannel, new WifiP2pManager.ActionListener() { // from class: jp.konami.peerlink.wifidirect.WifiDirect.4
                @Override // android.net.wifi.p2p.WifiP2pManager.ActionListener
                public void onFailure(int i) {
                    Logger.m968e("WifiDirect", "Failed to cancelConnect. (error = " + i + ")");
                }

                @Override // android.net.wifi.p2p.WifiP2pManager.ActionListener
                public void onSuccess() {
                    Logger.m967d("WifiDirect", "Canceled.");
                }
            });
        } else {
            wifiP2pManager.removeGroup(this.mChannel, new WifiP2pManager.ActionListener() { // from class: jp.konami.peerlink.wifidirect.WifiDirect.5
                @Override // android.net.wifi.p2p.WifiP2pManager.ActionListener
                public void onFailure(int i) {
                    Logger.m968e("WifiDirect", "Failed to removeGroup. (error = " + i + ")");
                }

                @Override // android.net.wifi.p2p.WifiP2pManager.ActionListener
                public void onSuccess() {
                    Logger.m967d("WifiDirect", "Closed.");
                }
            });
        }
        this.mNetworkInfo.changeConnectionState(NetworkInfo.ConnectionState.CLOSED);
        return true;
    }

    public boolean connect(ServiceInfo serviceInfo) {
        if (this.mWifiP2pManager == null || this.mChannel == null || this.mDeviceState == DeviceState.UNSUPPORTED || this.mDeviceState == DeviceState.INACTIVATED || this.mNetworkInfo.getConnectionState() != NetworkInfo.ConnectionState.OPEN) {
            return false;
        }
        final ServiceInfo serviceInfo2 = new ServiceInfo(serviceInfo);
        final WifiP2pDevice device = serviceInfo2.getDevice();
        if (device == null) {
            return false;
        }
        if (!device.wpsPbcSupported()) {
            Logger.m968e("WifiDirect", "WPS push button configuration is not supported.");
            return false;
        }
        WifiP2pConfig wifiP2pConfig = new WifiP2pConfig();
        wifiP2pConfig.deviceAddress = device.deviceAddress;
        wifiP2pConfig.wps.setup = 0;
        this.mWifiP2pManager.connect(this.mChannel, wifiP2pConfig, new WifiP2pManager.ActionListener() { // from class: jp.konami.peerlink.wifidirect.WifiDirect.3
            @Override // android.net.wifi.p2p.WifiP2pManager.ActionListener
            public void onFailure(int i) {
                Logger.m968e("WifiDirect", "Failed to connect. (error = " + i + ")");
                WifiDirect.this.mNetworkInfo.init();
            }

            @Override // android.net.wifi.p2p.WifiP2pManager.ActionListener
            public void onSuccess() {
                Logger.m967d("WifiDirect", "Connecting to: \n" + device.toString());
                WifiDirect.this.mNetworkInfo.set(serviceInfo2);
            }
        });
        this.mNetworkInfo.changeConnectionState(NetworkInfo.ConnectionState.CONNECTING);
        return true;
    }

    public boolean createGroup() {
        if (this.mWifiP2pManager == null || this.mChannel == null || this.mDeviceState == DeviceState.UNSUPPORTED || this.mDeviceState == DeviceState.INACTIVATED || this.mNetworkInfo.getConnectionState() != NetworkInfo.ConnectionState.OPEN) {
            return false;
        }
        this.mWifiP2pManager.createGroup(this.mChannel, new WifiP2pManager.ActionListener() { // from class: jp.konami.peerlink.wifidirect.WifiDirect.2
            @Override // android.net.wifi.p2p.WifiP2pManager.ActionListener
            public void onFailure(int i) {
                Logger.m968e("WifiDirect", "Failed to createGroup. (error = " + i + ")");
                WifiDirect.this.mNetworkInfo.init();
            }

            @Override // android.net.wifi.p2p.WifiP2pManager.ActionListener
            public void onSuccess() {
                Logger.m967d("WifiDirect", "Creating group...");
            }
        });
        this.mNetworkInfo.changeConnectionState(NetworkInfo.ConnectionState.CREATING);
        return true;
    }

    public void destruct() {
        Receiver receiver = this.mReceiver;
        if (receiver != null) {
            receiver.destruct();
            this.mReceiver = null;
        }
        stopAdvertisement();
        stopDiscovery();
        WifiDirectNsd wifiDirectNsd = this.mWifiDirectNsd;
        if (wifiDirectNsd != null) {
            wifiDirectNsd.destruct();
        }
        close();
        this.mChannel = null;
        this.mWifiP2pManager = null;
        this.mDeviceState = DeviceState.INACTIVATED;
        this.mNetworkInfo.init();
    }

    public AdvertisementState getAdvertisementState() {
        if (this.mDeviceState == DeviceState.UNSUPPORTED || this.mDeviceState == DeviceState.INACTIVATED) {
            return AdvertisementState.INACTIVATED;
        }
        WifiDirectNsd.ServiceInfo serviceInfo = new WifiDirectNsd.ServiceInfo();
        serviceInfo.setServiceName(this.mConfig.getId().toLowerCase());
        serviceInfo.setServiceType(this.mConfig.getServiceId());
        serviceInfo.setAttribute(ATTRIBUTE_KEY_ID, this.mConfig.getId());
        serviceInfo.setAttribute(ATTRIBUTE_KEY_PORT, String.valueOf(this.mConfig.getPort()));
        Map<String, String> attribute = this.mConfig.getAttribute();
        if (attribute != null) {
            try {
                serviceInfo.setAttribute(ATTRIBUTE_KEY_USER_ATTRIBUTE, new JSONObject(attribute).toString());
            } catch (NullPointerException e) {
                e.printStackTrace();
                return AdvertisementState.INACTIVATED;
            }
        }
        WifiDirectNsd.RegisterServiceState registerServiceState = this.mWifiDirectNsd.getRegisterServiceState(serviceInfo);
        return registerServiceState == WifiDirectNsd.RegisterServiceState.ACTIVATING ? AdvertisementState.ACTIVATING : registerServiceState == WifiDirectNsd.RegisterServiceState.ACTIVATED ? AdvertisementState.ACTIVATED : registerServiceState == WifiDirectNsd.RegisterServiceState.INACTIVATING ? AdvertisementState.INACTIVATING : registerServiceState == WifiDirectNsd.RegisterServiceState.INACTIVATED ? AdvertisementState.INACTIVATED : AdvertisementState.INACTIVATED;
    }

    public List<ServiceInfo> getDetectedServiceInfoList() {
        List<WifiDirectNsd.DetectedServiceInfo> detectedServiceInfoList;
        if (this.mDeviceState == DeviceState.UNSUPPORTED || this.mDeviceState == DeviceState.INACTIVATED || (detectedServiceInfoList = this.mWifiDirectNsd.getDetectedServiceInfoList()) == null || detectedServiceInfoList.size() == 0) {
            return null;
        }
        ArrayList arrayList = new ArrayList();
        Iterator<WifiDirectNsd.DetectedServiceInfo> it = detectedServiceInfoList.iterator();
        while (it.hasNext()) {
            arrayList.add(new ServiceInfo(it.next()));
        }
        if (arrayList.size() == 0) {
            return null;
        }
        return arrayList;
    }

    public DeviceState getDeviceState() {
        return this.mDeviceState;
    }

    public DiscoveryState getDiscoveryState() {
        if (this.mDeviceState == DeviceState.UNSUPPORTED || this.mDeviceState == DeviceState.INACTIVATED) {
            return DiscoveryState.INACTIVATED;
        }
        WifiDirectNsd.DiscoveryServiceInfo discoveryServiceInfo = new WifiDirectNsd.DiscoveryServiceInfo();
        discoveryServiceInfo.setServiceType(this.mConfig.getServiceId());
        WifiDirectNsd.RegisterDiscoveryServiceState registerDiscoveryServiceState = this.mWifiDirectNsd.getRegisterDiscoveryServiceState(discoveryServiceInfo);
        return registerDiscoveryServiceState == WifiDirectNsd.RegisterDiscoveryServiceState.ACTIVATING ? DiscoveryState.ACTIVATING : registerDiscoveryServiceState == WifiDirectNsd.RegisterDiscoveryServiceState.ACTIVATED ? DiscoveryState.ACTIVATED : registerDiscoveryServiceState == WifiDirectNsd.RegisterDiscoveryServiceState.INACTIVATING ? DiscoveryState.INACTIVATING : registerDiscoveryServiceState == WifiDirectNsd.RegisterDiscoveryServiceState.INACTIVATED ? DiscoveryState.INACTIVATED : DiscoveryState.INACTIVATED;
    }

    public NetworkInfo getNetworkInfo() {
        return this.mNetworkInfo;
    }

    public boolean startAdvertisement() {
        if (this.mDeviceState == DeviceState.UNSUPPORTED || this.mDeviceState == DeviceState.INACTIVATED) {
            return false;
        }
        WifiDirectNsd.ServiceInfo serviceInfo = new WifiDirectNsd.ServiceInfo();
        serviceInfo.setServiceName(this.mConfig.getId().toLowerCase());
        serviceInfo.setServiceType(this.mConfig.getServiceId());
        serviceInfo.setAttribute(ATTRIBUTE_KEY_ID, this.mConfig.getId());
        serviceInfo.setAttribute(ATTRIBUTE_KEY_PORT, String.valueOf(this.mConfig.getPort()));
        Map<String, String> attribute = this.mConfig.getAttribute();
        if (attribute != null) {
            try {
                serviceInfo.setAttribute(ATTRIBUTE_KEY_USER_ATTRIBUTE, new JSONObject(attribute).toString());
            } catch (NullPointerException e) {
                e.printStackTrace();
                return false;
            }
        }
        return this.mWifiDirectNsd.registerService(serviceInfo);
    }

    public boolean startDiscovery() {
        if (this.mDeviceState == DeviceState.UNSUPPORTED || this.mDeviceState == DeviceState.INACTIVATED) {
            return false;
        }
        WifiDirectNsd.DiscoveryServiceInfo discoveryServiceInfo = new WifiDirectNsd.DiscoveryServiceInfo();
        discoveryServiceInfo.setServiceType(this.mConfig.getServiceId());
        if (!this.mWifiDirectNsd.registerDiscoveryService(discoveryServiceInfo)) {
            return false;
        }
        if (this.mWifiDirectNsd.startDiscovery()) {
            return true;
        }
        if (!this.mWifiDirectNsd.unregisterDiscoveryService()) {
            Logger.m968e("WifiDirect", "Unknown error.");
        }
        return false;
    }

    public boolean stopAdvertisement() {
        return (this.mDeviceState == DeviceState.UNSUPPORTED || this.mDeviceState == DeviceState.INACTIVATED || !this.mWifiDirectNsd.unregisterService()) ? false : true;
    }

    public boolean stopDiscovery() {
        return this.mDeviceState != DeviceState.UNSUPPORTED && this.mDeviceState != DeviceState.INACTIVATED && this.mWifiDirectNsd.stopDiscovery() && this.mWifiDirectNsd.unregisterDiscoveryService();
    }
}
