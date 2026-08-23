package jp.konami.peerlink.wifidirect;

import android.net.wifi.p2p.WifiP2pDevice;
import android.net.wifi.p2p.WifiP2pManager;
import android.net.wifi.p2p.nsd.WifiP2pDnsSdServiceInfo;
import android.net.wifi.p2p.nsd.WifiP2pDnsSdServiceRequest;
import android.net.wifi.p2p.nsd.WifiP2pServiceInfo;
import android.net.wifi.p2p.nsd.WifiP2pServiceRequest;
import java.lang.reflect.InvocationTargetException;
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

/* JADX INFO: loaded from: classes3.dex */
public class WifiDirectNsd {
    private WifiP2pManager.Channel mChannel;
    private WifiP2pManager mWifiP2pManager;
    private final Map<ServiceInfo, WifiP2pServiceInfo> mRegisteredService = new HashMap();
    private final Map<DiscoveryServiceInfo, WifiP2pServiceRequest> mRegisteredDiscoveryService = new HashMap();
    private final DiscoverService mDiscoverService = new DiscoverService();
    private final Map<String, TxtRecordInfo> mTxtRecord = new HashMap();
    private final Map<DiscoveredServiceInfo, Integer> mDiscoveredService = new HashMap();

    public static class DetectedServiceInfo {
        private Map mAttribute;
        private WifiP2pDevice mDevice;
        private String mServiceName;
        private String mServiceType;

        public DetectedServiceInfo() {
        }

        public DetectedServiceInfo(DetectedServiceInfo detectedServiceInfo) {
            this.mServiceName = detectedServiceInfo.mServiceName;
            this.mServiceType = detectedServiceInfo.mServiceType;
            Map map = detectedServiceInfo.mAttribute;
            if (map != null) {
                try {
                    this.mAttribute = (Map) map.getClass().getConstructor(Map.class).newInstance(map);
                } catch (IllegalAccessException e) {
                    throw new RuntimeException(e);
                } catch (IllegalArgumentException e2) {
                    throw new RuntimeException(e2);
                } catch (InstantiationException e3) {
                    throw new RuntimeException(e3);
                } catch (NoSuchMethodException e4) {
                    throw new RuntimeException(e4);
                } catch (InvocationTargetException e5) {
                    throw new RuntimeException(e5);
                }
            }
            this.mDevice = new WifiP2pDevice(detectedServiceInfo.mDevice);
        }

        /* JADX INFO: Access modifiers changed from: private */
        public void setAttribute(Map map) {
            if (map == null) {
                this.mAttribute = null;
                return;
            }
            try {
                this.mAttribute = (Map) map.getClass().getConstructor(Map.class).newInstance(map);
            } catch (IllegalAccessException e) {
                throw new RuntimeException(e);
            } catch (IllegalArgumentException e2) {
                throw new RuntimeException(e2);
            } catch (InstantiationException e3) {
                throw new RuntimeException(e3);
            } catch (NoSuchMethodException e4) {
                throw new RuntimeException(e4);
            } catch (InvocationTargetException e5) {
                throw new RuntimeException(e5);
            }
        }

        /* JADX INFO: Access modifiers changed from: private */
        public void setDevice(WifiP2pDevice wifiP2pDevice) {
            if (wifiP2pDevice == null) {
                this.mDevice = null;
            } else {
                this.mDevice = new WifiP2pDevice(wifiP2pDevice);
            }
        }

        /* JADX INFO: Access modifiers changed from: private */
        public void setServiceName(String str) {
            this.mServiceName = str;
        }

        /* JADX INFO: Access modifiers changed from: private */
        public void setServiceType(String str) {
            this.mServiceType = str;
        }

        public boolean equals(Object obj) {
            if (obj == null) {
                return false;
            }
            if (!(obj instanceof DetectedServiceInfo)) {
                return super.equals(obj);
            }
            DetectedServiceInfo detectedServiceInfo = (DetectedServiceInfo) obj;
            String str = this.mServiceName;
            if (str != null ? str.equals(detectedServiceInfo.mServiceName) : detectedServiceInfo.mServiceName == null) {
                String str2 = this.mServiceType;
                if (str2 != null ? str2.equals(detectedServiceInfo.mServiceType) : detectedServiceInfo.mServiceType == null) {
                    Map map = this.mAttribute;
                    if (map != null ? map.equals(detectedServiceInfo.mAttribute) : detectedServiceInfo.mAttribute == null) {
                        WifiP2pDevice wifiP2pDevice = this.mDevice;
                        WifiP2pDevice wifiP2pDevice2 = detectedServiceInfo.mDevice;
                        if (wifiP2pDevice == null) {
                            if (wifiP2pDevice2 == null) {
                                return true;
                            }
                        } else if (wifiP2pDevice.equals(wifiP2pDevice2)) {
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

        public WifiP2pDevice getDevice() {
            return this.mDevice;
        }

        public String getServiceName() {
            return this.mServiceName;
        }

        public String getServiceType() {
            return this.mServiceType;
        }

        public int hashCode() {
            String str = this.mServiceName;
            int iHashCode = str == null ? 0 : str.hashCode();
            String str2 = this.mServiceType;
            int iHashCode2 = iHashCode + (str2 == null ? 0 : str2.hashCode());
            Map map = this.mAttribute;
            return iHashCode2 + (map != null ? map.hashCode() : 0);
        }
    }

    private class DiscoverService {
        private static final int EXPIRE_TIME = 2;
        private static final long INTERVAL_MS = 5000;
        private ScheduledFuture<?> mFuture;
        private ScheduledExecutorService mService;

        private class Task implements Runnable {
            private Task() {
            }

            @Override // java.lang.Runnable
            public void run() {
                synchronized (WifiDirectNsd.this.mDiscoveredService) {
                    Iterator it = WifiDirectNsd.this.mDiscoveredService.entrySet().iterator();
                    while (it.hasNext()) {
                        Map.Entry entry = (Map.Entry) it.next();
                        WifiDirectNsd.this.mDiscoveredService.put((DiscoveredServiceInfo) entry.getKey(), Integer.valueOf(((Integer) entry.getValue()).intValue() + 1));
                        if (((Integer) entry.getValue()).intValue() >= 2) {
                            it.remove();
                        }
                    }
                }
                WifiDirectNsd.this.mWifiP2pManager.discoverServices(WifiDirectNsd.this.mChannel, new WifiP2pManager.ActionListener() { // from class: jp.konami.peerlink.wifidirect.WifiDirectNsd.DiscoverService.Task.1
                    @Override // android.net.wifi.p2p.WifiP2pManager.ActionListener
                    public void onFailure(int i) {
                        Logger.m968e("WifiDirectNsd", "Discover service failed. (error = " + String.valueOf(i) + ")");
                    }

                    @Override // android.net.wifi.p2p.WifiP2pManager.ActionListener
                    public void onSuccess() {
                        Logger.m967d("WifiDirectNsd", "Discover service.");
                    }
                });
            }
        }

        private DiscoverService() {
            this.mService = Executors.newSingleThreadScheduledExecutor();
            this.mFuture = null;
        }

        public void destruct() {
            ScheduledExecutorService scheduledExecutorService = this.mService;
            if (scheduledExecutorService != null) {
                scheduledExecutorService.shutdownNow();
                this.mService = null;
            }
        }

        protected void finalize() {
            destruct();
        }

        public boolean start() {
            ScheduledExecutorService scheduledExecutorService = this.mService;
            if (scheduledExecutorService == null) {
                return false;
            }
            this.mFuture = scheduledExecutorService.scheduleWithFixedDelay(new Task(), 0L, 5000L, TimeUnit.MILLISECONDS);
            return true;
        }

        public void stop() {
            ScheduledFuture<?> scheduledFuture = this.mFuture;
            if (scheduledFuture != null) {
                scheduledFuture.cancel(true);
            }
        }
    }

    private static class DiscoveredServiceInfo {
        private WifiP2pDevice mDevice;
        private String mInstanceName;
        private String mRegistrationType;

        DiscoveredServiceInfo(String str, String str2, WifiP2pDevice wifiP2pDevice) {
            this.mInstanceName = str;
            this.mRegistrationType = str2;
            if (wifiP2pDevice != null) {
                this.mDevice = new WifiP2pDevice(wifiP2pDevice);
            }
        }

        public boolean equals(Object obj) {
            if (obj == null) {
                return false;
            }
            if (!(obj instanceof DiscoveredServiceInfo)) {
                return super.equals(obj);
            }
            DiscoveredServiceInfo discoveredServiceInfo = (DiscoveredServiceInfo) obj;
            String str = this.mInstanceName;
            if (str != null ? str.equals(discoveredServiceInfo.mInstanceName) : discoveredServiceInfo.mInstanceName == null) {
                String str2 = this.mRegistrationType;
                if (str2 != null ? str2.equals(discoveredServiceInfo.mRegistrationType) : discoveredServiceInfo.mRegistrationType == null) {
                    WifiP2pDevice wifiP2pDevice = this.mDevice;
                    WifiP2pDevice wifiP2pDevice2 = discoveredServiceInfo.mDevice;
                    if (wifiP2pDevice == null) {
                        if (wifiP2pDevice2 == null) {
                            return true;
                        }
                    } else if (wifiP2pDevice.equals(wifiP2pDevice2)) {
                        return true;
                    }
                }
            }
            return false;
        }

        public int hashCode() {
            String str = this.mInstanceName;
            int iHashCode = str == null ? 0 : str.hashCode();
            String str2 = this.mRegistrationType;
            return iHashCode + (str2 != null ? str2.hashCode() : 0);
        }
    }

    public static class DiscoveryServiceInfo {
        private String mServiceType;

        public DiscoveryServiceInfo() {
        }

        public DiscoveryServiceInfo(DiscoveryServiceInfo discoveryServiceInfo) {
            this.mServiceType = discoveryServiceInfo.mServiceType;
        }

        /* JADX INFO: Access modifiers changed from: private */
        public boolean isValid() {
            return WifiDirectNsd.isServiceTypeValid(this.mServiceType);
        }

        public boolean equals(Object obj) {
            if (obj == null) {
                return false;
            }
            if (!(obj instanceof DiscoveryServiceInfo)) {
                return super.equals(obj);
            }
            String str = this.mServiceType;
            String str2 = ((DiscoveryServiceInfo) obj).mServiceType;
            return str == null ? str2 == null : str.equals(str2);
        }

        public String getServiceType() {
            return this.mServiceType;
        }

        public int hashCode() {
            String str = this.mServiceType;
            if (str == null) {
                return 0;
            }
            return str.hashCode();
        }

        public void setServiceType(String str) {
            this.mServiceType = str;
        }
    }

    public enum RegisterDiscoveryServiceState {
        ACTIVATING,
        ACTIVATED,
        INACTIVATING,
        INACTIVATED
    }

    public enum RegisterServiceState {
        ACTIVATING,
        ACTIVATED,
        INACTIVATING,
        INACTIVATED
    }

    public static class ServiceInfo {
        private Map mAttribute;
        private String mServiceName;
        private String mServiceType;

        public ServiceInfo() {
        }

        public ServiceInfo(ServiceInfo serviceInfo) {
            this.mServiceName = serviceInfo.mServiceName;
            this.mServiceType = serviceInfo.mServiceType;
            Map map = serviceInfo.mAttribute;
            if (map != null) {
                try {
                    this.mAttribute = (Map) map.getClass().getConstructor(Map.class).newInstance(map);
                } catch (IllegalAccessException e) {
                    throw new RuntimeException(e);
                } catch (IllegalArgumentException e2) {
                    throw new RuntimeException(e2);
                } catch (InstantiationException e3) {
                    throw new RuntimeException(e3);
                } catch (NoSuchMethodException e4) {
                    throw new RuntimeException(e4);
                } catch (InvocationTargetException e5) {
                    throw new RuntimeException(e5);
                }
            }
        }

        /* JADX INFO: Access modifiers changed from: private */
        public boolean isValid() {
            return WifiDirectNsd.isServiceNameValid(this.mServiceName) && WifiDirectNsd.isServiceTypeValid(this.mServiceType);
        }

        public boolean equals(Object obj) {
            if (obj == null) {
                return false;
            }
            if (!(obj instanceof ServiceInfo)) {
                return super.equals(obj);
            }
            ServiceInfo serviceInfo = (ServiceInfo) obj;
            String str = this.mServiceName;
            if (str != null ? str.equals(serviceInfo.mServiceName) : serviceInfo.mServiceName == null) {
                String str2 = this.mServiceType;
                if (str2 != null ? str2.equals(serviceInfo.mServiceType) : serviceInfo.mServiceType == null) {
                    Map map = this.mAttribute;
                    Map map2 = serviceInfo.mAttribute;
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

        public String getServiceName() {
            return this.mServiceName;
        }

        public String getServiceType() {
            return this.mServiceType;
        }

        public int hashCode() {
            String str = this.mServiceName;
            int iHashCode = str == null ? 0 : str.hashCode();
            String str2 = this.mServiceType;
            int iHashCode2 = iHashCode + (str2 == null ? 0 : str2.hashCode());
            Map map = this.mAttribute;
            return iHashCode2 + (map != null ? map.hashCode() : 0);
        }

        public void setAttribute(String str, String str2) {
            if (this.mAttribute == null) {
                this.mAttribute = new HashMap();
            }
            this.mAttribute.put(str, str2);
        }

        public void setServiceName(String str) {
            this.mServiceName = str;
        }

        public void setServiceType(String str) {
            this.mServiceType = str;
        }
    }

    private static class TxtRecordInfo {
        private WifiP2pDevice mDevice;
        private Map mTxtRecord;

        TxtRecordInfo(Map map, WifiP2pDevice wifiP2pDevice) {
            if (map != null) {
                try {
                    this.mTxtRecord = (Map) map.getClass().getConstructor(Map.class).newInstance(map);
                } catch (IllegalAccessException e) {
                    throw new RuntimeException(e);
                } catch (IllegalArgumentException e2) {
                    throw new RuntimeException(e2);
                } catch (InstantiationException e3) {
                    throw new RuntimeException(e3);
                } catch (NoSuchMethodException e4) {
                    throw new RuntimeException(e4);
                } catch (InvocationTargetException e5) {
                    throw new RuntimeException(e5);
                }
            }
            if (wifiP2pDevice != null) {
                this.mDevice = new WifiP2pDevice(wifiP2pDevice);
            }
        }
    }

    public WifiDirectNsd(WifiP2pManager wifiP2pManager, WifiP2pManager.Channel channel) {
        this.mWifiP2pManager = wifiP2pManager;
        this.mChannel = channel;
        wifiP2pManager.setDnsSdResponseListeners(channel, new WifiP2pManager.DnsSdServiceResponseListener() { // from class: jp.konami.peerlink.wifidirect.WifiDirectNsd.1
            @Override // android.net.wifi.p2p.WifiP2pManager.DnsSdServiceResponseListener
            public void onDnsSdServiceAvailable(String str, String str2, WifiP2pDevice wifiP2pDevice) {
                Logger.m967d("WifiDirectNsd", "DnsSdService available: instance = " + str + ", registration = " + str2 + ", device = " + wifiP2pDevice.toString());
                synchronized (WifiDirectNsd.this.mDiscoveredService) {
                    WifiDirectNsd.this.mDiscoveredService.put(new DiscoveredServiceInfo(str, str2, wifiP2pDevice), 0);
                }
            }
        }, new WifiP2pManager.DnsSdTxtRecordListener() { // from class: jp.konami.peerlink.wifidirect.WifiDirectNsd.2
            @Override // android.net.wifi.p2p.WifiP2pManager.DnsSdTxtRecordListener
            public void onDnsSdTxtRecordAvailable(String str, Map<String, String> map, WifiP2pDevice wifiP2pDevice) {
                Logger.m967d("WifiDirectNsd", "DnsSdTxtRecord available: domain = " + str + ", record = " + map.toString() + ", device = " + wifiP2pDevice.toString());
                WifiDirectNsd.this.mTxtRecord.put(str, new TxtRecordInfo(map, wifiP2pDevice));
            }
        });
    }

    /* JADX INFO: Access modifiers changed from: private */
    public static boolean isServiceNameValid(String str) {
        return (str == null || str.isEmpty() || Pattern.compile("[^a-z0-9-]").matcher(str).find()) ? false : true;
    }

    /* JADX INFO: Access modifiers changed from: private */
    public static boolean isServiceTypeValid(String str) {
        return (str == null || str.isEmpty() || Pattern.compile("[^a-z0-9-]").matcher(str).find()) ? false : true;
    }

    public void destruct() {
        unregisterService();
        unregisterDiscoveryService();
        this.mDiscoverService.destruct();
        this.mRegisteredService.clear();
        this.mRegisteredDiscoveryService.clear();
        this.mTxtRecord.clear();
        synchronized (this.mDiscoveredService) {
            this.mDiscoveredService.clear();
        }
        this.mChannel = null;
        this.mWifiP2pManager = null;
    }

    public List<DetectedServiceInfo> getDetectedServiceInfoList() {
        ArrayList arrayList;
        synchronized (this.mDiscoveredService) {
            arrayList = null;
            for (DiscoveredServiceInfo discoveredServiceInfo : this.mDiscoveredService.keySet()) {
                Iterator<DiscoveryServiceInfo> it = this.mRegisteredDiscoveryService.keySet().iterator();
                while (true) {
                    if (it.hasNext()) {
                        if (discoveredServiceInfo.mRegistrationType.startsWith(it.next().getServiceType())) {
                            TxtRecordInfo txtRecordInfo = this.mTxtRecord.get(discoveredServiceInfo.mInstanceName + "." + discoveredServiceInfo.mRegistrationType);
                            if (txtRecordInfo != null) {
                                DetectedServiceInfo detectedServiceInfo = new DetectedServiceInfo();
                                detectedServiceInfo.setServiceName(discoveredServiceInfo.mInstanceName);
                                detectedServiceInfo.setServiceType(discoveredServiceInfo.mRegistrationType);
                                detectedServiceInfo.setAttribute(txtRecordInfo.mTxtRecord);
                                detectedServiceInfo.setDevice(txtRecordInfo.mDevice);
                                if (arrayList == null) {
                                    arrayList = new ArrayList();
                                }
                                arrayList.add(detectedServiceInfo);
                            }
                        }
                    }
                }
            }
        }
        return arrayList;
    }

    public RegisterDiscoveryServiceState getRegisterDiscoveryServiceState(DiscoveryServiceInfo discoveryServiceInfo) {
        return !this.mRegisteredDiscoveryService.containsKey(discoveryServiceInfo) ? RegisterDiscoveryServiceState.INACTIVATED : RegisterDiscoveryServiceState.ACTIVATED;
    }

    public RegisterServiceState getRegisterServiceState(ServiceInfo serviceInfo) {
        return !this.mRegisteredService.containsKey(serviceInfo) ? RegisterServiceState.INACTIVATED : RegisterServiceState.ACTIVATED;
    }

    public boolean registerDiscoveryService(DiscoveryServiceInfo discoveryServiceInfo) {
        if (this.mWifiP2pManager == null || this.mChannel == null || !discoveryServiceInfo.isValid() || this.mRegisteredDiscoveryService.containsKey(discoveryServiceInfo)) {
            return false;
        }
        final DiscoveryServiceInfo discoveryServiceInfo2 = new DiscoveryServiceInfo(discoveryServiceInfo);
        WifiP2pDnsSdServiceRequest wifiP2pDnsSdServiceRequestNewInstance = WifiP2pDnsSdServiceRequest.newInstance();
        this.mRegisteredDiscoveryService.put(discoveryServiceInfo2, wifiP2pDnsSdServiceRequestNewInstance);
        this.mWifiP2pManager.addServiceRequest(this.mChannel, wifiP2pDnsSdServiceRequestNewInstance, new WifiP2pManager.ActionListener() { // from class: jp.konami.peerlink.wifidirect.WifiDirectNsd.6
            @Override // android.net.wifi.p2p.WifiP2pManager.ActionListener
            public void onFailure(int i) {
                WifiDirectNsd.this.mRegisteredDiscoveryService.remove(discoveryServiceInfo2);
                Logger.m968e("WifiDirectNsd", "Register request failed. (error = " + String.valueOf(i) + ")");
            }

            @Override // android.net.wifi.p2p.WifiP2pManager.ActionListener
            public void onSuccess() {
                Logger.m967d("WifiDirectNsd", "Registered request.");
            }
        });
        return true;
    }

    public boolean registerService(ServiceInfo serviceInfo) {
        if (this.mWifiP2pManager == null || this.mChannel == null || !serviceInfo.isValid() || this.mRegisteredService.containsKey(serviceInfo)) {
            return false;
        }
        final ServiceInfo serviceInfo2 = new ServiceInfo(serviceInfo);
        WifiP2pDnsSdServiceInfo wifiP2pDnsSdServiceInfoNewInstance = WifiP2pDnsSdServiceInfo.newInstance(serviceInfo2.getServiceName(), serviceInfo2.getServiceType(), serviceInfo2.getAttribute());
        this.mRegisteredService.put(serviceInfo2, wifiP2pDnsSdServiceInfoNewInstance);
        this.mWifiP2pManager.addLocalService(this.mChannel, wifiP2pDnsSdServiceInfoNewInstance, new WifiP2pManager.ActionListener() { // from class: jp.konami.peerlink.wifidirect.WifiDirectNsd.3
            @Override // android.net.wifi.p2p.WifiP2pManager.ActionListener
            public void onFailure(int i) {
                WifiDirectNsd.this.mRegisteredService.remove(serviceInfo2);
                Logger.m968e("WifiDirectNsd", "Register service failed. (error = " + String.valueOf(i) + ")");
            }

            @Override // android.net.wifi.p2p.WifiP2pManager.ActionListener
            public void onSuccess() {
                Logger.m967d("WifiDirectNsd", "Registered service.");
            }
        });
        return true;
    }

    public boolean startDiscovery() {
        synchronized (this.mDiscoveredService) {
            this.mDiscoveredService.clear();
        }
        return this.mDiscoverService.start();
    }

    public boolean stopDiscovery() {
        this.mDiscoverService.stop();
        synchronized (this.mDiscoveredService) {
            this.mDiscoveredService.clear();
        }
        return true;
    }

    public boolean unregisterDiscoveryService() {
        WifiP2pManager.Channel channel;
        WifiP2pManager wifiP2pManager = this.mWifiP2pManager;
        if (wifiP2pManager == null || (channel = this.mChannel) == null) {
            return false;
        }
        wifiP2pManager.clearServiceRequests(channel, new WifiP2pManager.ActionListener() { // from class: jp.konami.peerlink.wifidirect.WifiDirectNsd.8
            @Override // android.net.wifi.p2p.WifiP2pManager.ActionListener
            public void onFailure(int i) {
                Logger.m968e("WifiDirectNsd", "Stop discovery services failed. (error = " + String.valueOf(i) + ")");
            }

            @Override // android.net.wifi.p2p.WifiP2pManager.ActionListener
            public void onSuccess() {
                WifiDirectNsd.this.mRegisteredDiscoveryService.clear();
                Logger.m967d("WifiDirectNsd", "Stopped discovery services.");
            }
        });
        return true;
    }

    public boolean unregisterDiscoveryService(DiscoveryServiceInfo discoveryServiceInfo) {
        final DiscoveryServiceInfo discoveryServiceInfo2;
        WifiP2pServiceRequest wifiP2pServiceRequest;
        if (this.mWifiP2pManager == null || this.mChannel == null || (wifiP2pServiceRequest = this.mRegisteredDiscoveryService.get((discoveryServiceInfo2 = new DiscoveryServiceInfo(discoveryServiceInfo)))) == null) {
            return false;
        }
        this.mWifiP2pManager.removeServiceRequest(this.mChannel, wifiP2pServiceRequest, new WifiP2pManager.ActionListener() { // from class: jp.konami.peerlink.wifidirect.WifiDirectNsd.7
            @Override // android.net.wifi.p2p.WifiP2pManager.ActionListener
            public void onFailure(int i) {
                Logger.m968e("WifiDirectNsd", "Stop discovery service failed. (error = " + String.valueOf(i) + ")");
            }

            @Override // android.net.wifi.p2p.WifiP2pManager.ActionListener
            public void onSuccess() {
                WifiDirectNsd.this.mRegisteredDiscoveryService.remove(discoveryServiceInfo2);
                Logger.m967d("WifiDirectNsd", "Stopped discovery service.");
            }
        });
        return true;
    }

    public boolean unregisterService() {
        WifiP2pManager.Channel channel;
        WifiP2pManager wifiP2pManager = this.mWifiP2pManager;
        if (wifiP2pManager == null || (channel = this.mChannel) == null) {
            return false;
        }
        wifiP2pManager.clearLocalServices(channel, new WifiP2pManager.ActionListener() { // from class: jp.konami.peerlink.wifidirect.WifiDirectNsd.5
            @Override // android.net.wifi.p2p.WifiP2pManager.ActionListener
            public void onFailure(int i) {
                Logger.m968e("WifiDirectNsd", "Unregister services failed. (error = " + String.valueOf(i) + ")");
            }

            @Override // android.net.wifi.p2p.WifiP2pManager.ActionListener
            public void onSuccess() {
                WifiDirectNsd.this.mRegisteredService.clear();
                Logger.m967d("WifiDirectNsd", "Unregistered services.");
            }
        });
        return true;
    }

    public boolean unregisterService(ServiceInfo serviceInfo) {
        final ServiceInfo serviceInfo2;
        WifiP2pServiceInfo wifiP2pServiceInfo;
        if (this.mWifiP2pManager == null || this.mChannel == null || (wifiP2pServiceInfo = this.mRegisteredService.get((serviceInfo2 = new ServiceInfo(serviceInfo)))) == null) {
            return false;
        }
        this.mWifiP2pManager.removeLocalService(this.mChannel, wifiP2pServiceInfo, new WifiP2pManager.ActionListener() { // from class: jp.konami.peerlink.wifidirect.WifiDirectNsd.4
            @Override // android.net.wifi.p2p.WifiP2pManager.ActionListener
            public void onFailure(int i) {
                Logger.m968e("WifiDirectNsd", "Unregister service failed. (error = " + String.valueOf(i) + ")");
            }

            @Override // android.net.wifi.p2p.WifiP2pManager.ActionListener
            public void onSuccess() {
                WifiDirectNsd.this.mRegisteredService.remove(serviceInfo2);
                Logger.m967d("WifiDirectNsd", "Unregistered service.");
            }
        });
        return true;
    }
}