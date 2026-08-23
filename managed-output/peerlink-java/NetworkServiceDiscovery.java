package jp.konami.peerlink.nsd;

import android.app.Activity;
import android.net.wifi.WifiManager;
import java.lang.reflect.InvocationTargetException;
import java.net.Inet4Address;
import java.net.Inet6Address;
import java.net.InetAddress;
import java.net.NetworkInterface;
import java.util.AbstractMap;
import java.util.ArrayList;
import java.util.Enumeration;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import javax.jmdns.JmDNS;
import javax.jmdns.ServiceEvent;
import javax.jmdns.ServiceListener;
import jp.konami.Logger;

/* JADX INFO: loaded from: classes3.dex */
public class NetworkServiceDiscovery {
    private JmDNS mJmDNS4;
    private JmDNS mJmDNS6;
    private WifiManager.MulticastLock mMulticastLock;
    private final ExecutorService mExecutorService = Executors.newSingleThreadExecutor();
    private final Set<ServiceInfo> mRegisteredServiceInfoSet = new HashSet();
    private final Set<DiscoveryServiceInfo> mDiscoveryServiceInfoSet = new HashSet();
    private final Map<AbstractMap.SimpleImmutableEntry<String, String>, DetectedServiceInfo> mDetectedServiceInfoMap = new HashMap();

    public static class DetectedServiceInfo {
        private Map mAttribute;
        private String mHostName;
        private int mPort;
        private String mServiceName;
        private String mServiceType;

        public DetectedServiceInfo() {
            this.mPort = 0;
        }

        public DetectedServiceInfo(DetectedServiceInfo detectedServiceInfo) {
            this.mPort = 0;
            this.mServiceName = detectedServiceInfo.mServiceName;
            this.mServiceType = detectedServiceInfo.mServiceType;
            this.mHostName = detectedServiceInfo.mHostName;
            this.mPort = detectedServiceInfo.mPort;
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
        public void setHostName(String str) {
            this.mHostName = str;
        }

        /* JADX INFO: Access modifiers changed from: private */
        public void setPort(int i) {
            this.mPort = i;
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
                    String str3 = this.mHostName;
                    if (str3 != null ? str3.equals(detectedServiceInfo.mHostName) : detectedServiceInfo.mHostName == null) {
                        if (this.mPort == detectedServiceInfo.mPort) {
                            Map map = this.mAttribute;
                            Map map2 = detectedServiceInfo.mAttribute;
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
            }
            return false;
        }

        public Map<String, String> getAttribute() {
            return this.mAttribute;
        }

        public String getHostName() {
            return this.mHostName;
        }

        public int getPort() {
            return this.mPort;
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
            String str3 = this.mHostName;
            int iHashCode3 = iHashCode2 + (str3 == null ? 0 : str3.hashCode()) + this.mPort;
            Map map = this.mAttribute;
            return iHashCode3 + (map != null ? map.hashCode() : 0);
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
            String str = this.mServiceType;
            return (str == null || str.isEmpty()) ? false : true;
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

    public static class ServiceInfo {
        private Map mAttribute;
        private int mPort;
        private String mServiceName;
        private String mServiceType;

        public ServiceInfo() {
            this.mPort = 0;
        }

        public ServiceInfo(ServiceInfo serviceInfo) {
            this.mPort = 0;
            this.mServiceName = serviceInfo.mServiceName;
            this.mServiceType = serviceInfo.mServiceType;
            this.mPort = serviceInfo.mPort;
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
            String str;
            String str2 = this.mServiceName;
            return (str2 == null || str2.isEmpty() || (str = this.mServiceType) == null || str.isEmpty() || this.mPort <= 0) ? false : true;
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
                    if (this.mPort == serviceInfo.mPort) {
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
            }
            return false;
        }

        public Map<String, String> getAttribute() {
            return this.mAttribute;
        }

        public int getPort() {
            return this.mPort;
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
            int iHashCode2 = iHashCode + (str2 == null ? 0 : str2.hashCode()) + this.mPort;
            Map map = this.mAttribute;
            return iHashCode2 + (map != null ? map.hashCode() : 0);
        }

        public void setAttribute(String str, String str2) {
            if (this.mAttribute == null) {
                this.mAttribute = new HashMap();
            }
            this.mAttribute.put(str, str2);
        }

        public void setPort(int i) {
            this.mPort = i;
        }

        public void setServiceName(String str) {
            this.mServiceName = str;
        }

        public void setServiceType(String str) {
            this.mServiceType = str;
        }
    }

    public NetworkServiceDiscovery(Activity activity) {
        WifiManager wifiManager;
        if (activity == null || (wifiManager = (WifiManager) activity.getSystemService("wifi")) == null) {
            return;
        }
        WifiManager.MulticastLock multicastLockCreateMulticastLock = wifiManager.createMulticastLock("NetworkServiceDiscovery");
        this.mMulticastLock = multicastLockCreateMulticastLock;
        if (multicastLockCreateMulticastLock == null) {
            return;
        }
        multicastLockCreateMulticastLock.setReferenceCounted(true);
        this.mMulticastLock.acquire();
        try {
            Enumeration<NetworkInterface> networkInterfaces = NetworkInterface.getNetworkInterfaces();
            while (networkInterfaces.hasMoreElements()) {
                Enumeration<InetAddress> inetAddresses = networkInterfaces.nextElement().getInetAddresses();
                while (inetAddresses.hasMoreElements()) {
                    InetAddress inetAddressNextElement = inetAddresses.nextElement();
                    if (!inetAddressNextElement.isLoopbackAddress() && !inetAddressNextElement.isLinkLocalAddress()) {
                        if (inetAddressNextElement instanceof Inet4Address) {
                            if (this.mJmDNS4 == null) {
                                this.mJmDNS4 = JmDNS.create(inetAddressNextElement);
                            }
                        } else if ((inetAddressNextElement instanceof Inet6Address) && this.mJmDNS6 == null) {
                            this.mJmDNS6 = JmDNS.create(inetAddressNextElement);
                        }
                    }
                }
            }
        } catch (Throwable th) {
            th.printStackTrace();
            destruct();
        }
    }

    public void destruct() {
        unregisterService();
        stopServiceDiscovery();
        WifiManager.MulticastLock multicastLock = this.mMulticastLock;
        if (multicastLock != null && multicastLock.isHeld()) {
            this.mMulticastLock.release();
            this.mMulticastLock = null;
        }
        final JmDNS jmDNS = this.mJmDNS4;
        this.mJmDNS4 = null;
        final JmDNS jmDNS2 = this.mJmDNS6;
        this.mJmDNS6 = null;
        this.mExecutorService.execute(new Runnable() { // from class: jp.konami.peerlink.nsd.NetworkServiceDiscovery.1
            @Override // java.lang.Runnable
            public void run() {
                JmDNS jmDNS3 = jmDNS;
                if (jmDNS3 != null) {
                    try {
                        jmDNS3.close();
                    } catch (Throwable th) {
                        th.printStackTrace();
                    }
                }
                JmDNS jmDNS4 = jmDNS2;
                if (jmDNS4 != null) {
                    try {
                        jmDNS4.close();
                    } catch (Throwable th2) {
                        th2.printStackTrace();
                    }
                }
            }
        });
        this.mExecutorService.shutdown();
    }

    public List<DetectedServiceInfo> getDetectedServiceInfoList() {
        if (this.mJmDNS4 == null && this.mJmDNS6 == null) {
            return null;
        }
        synchronized (this.mDetectedServiceInfoMap) {
            if (this.mDetectedServiceInfoMap.isEmpty()) {
                return null;
            }
            ArrayList arrayList = new ArrayList();
            Iterator<DetectedServiceInfo> it = this.mDetectedServiceInfoMap.values().iterator();
            while (it.hasNext()) {
                DetectedServiceInfo detectedServiceInfo = new DetectedServiceInfo(it.next());
                detectedServiceInfo.setServiceType(detectedServiceInfo.getServiceType().replaceFirst("local.$", ""));
                arrayList.add(detectedServiceInfo);
            }
            if (arrayList.size() == 0) {
                return null;
            }
            return arrayList;
        }
    }

    public List<ServiceInfo> getRegisteredServiceInfoList() {
        if (this.mJmDNS4 == null && this.mJmDNS6 == null) {
            return null;
        }
        synchronized (this.mRegisteredServiceInfoSet) {
            if (this.mRegisteredServiceInfoSet.isEmpty()) {
                return null;
            }
            ArrayList arrayList = new ArrayList();
            Iterator<ServiceInfo> it = this.mRegisteredServiceInfoSet.iterator();
            while (it.hasNext()) {
                arrayList.add(new ServiceInfo(it.next()));
            }
            if (arrayList.size() == 0) {
                return null;
            }
            return arrayList;
        }
    }

    public boolean registerService(final ServiceInfo serviceInfo) {
        if (this.mJmDNS4 == null && this.mJmDNS6 == null) {
            return false;
        }
        serviceInfo.setServiceType(serviceInfo.getServiceType() + "local.");
        if (!serviceInfo.isValid()) {
            return false;
        }
        this.mExecutorService.execute(new Runnable() { // from class: jp.konami.peerlink.nsd.NetworkServiceDiscovery.2
            @Override // java.lang.Runnable
            public void run() {
                javax.jmdns.ServiceInfo serviceInfoCreate = javax.jmdns.ServiceInfo.create(serviceInfo.getServiceType(), serviceInfo.getServiceName(), serviceInfo.getPort(), 0, 0, true, (Map<String, ?>) serviceInfo.getAttribute());
                javax.jmdns.ServiceInfo serviceInfoClone = serviceInfoCreate.clone();
                try {
                    if (NetworkServiceDiscovery.this.mJmDNS4 != null) {
                        NetworkServiceDiscovery.this.mJmDNS4.registerService(serviceInfoCreate);
                    }
                    if (NetworkServiceDiscovery.this.mJmDNS6 != null) {
                        NetworkServiceDiscovery.this.mJmDNS6.registerService(serviceInfoClone);
                    }
                    Logger.m967d("NetworkServiceDiscovery", "Registered service: \n" + serviceInfoClone.toString());
                    if (!serviceInfoClone.getName().equals(serviceInfo.getServiceName())) {
                        Logger.m967d("NetworkServiceDiscovery", "Changed service name: " + serviceInfo.getServiceName() + " -> " + serviceInfoClone.getName());
                        serviceInfo.setServiceName(serviceInfoClone.getName());
                    }
                    synchronized (NetworkServiceDiscovery.this.mRegisteredServiceInfoSet) {
                        if (!NetworkServiceDiscovery.this.mRegisteredServiceInfoSet.add(serviceInfo)) {
                            Logger.m968e("NetworkServiceDiscovery", "Unknown error.");
                        }
                    }
                } catch (Throwable th) {
                    Logger.m968e("NetworkServiceDiscovery", "Registration failed.");
                    th.printStackTrace();
                }
            }
        });
        return true;
    }

    public boolean startServiceDiscovery(DiscoveryServiceInfo discoveryServiceInfo) {
        if (this.mJmDNS4 == null && this.mJmDNS6 == null) {
            return false;
        }
        discoveryServiceInfo.setServiceType(discoveryServiceInfo.getServiceType() + "local.");
        if (!discoveryServiceInfo.isValid()) {
            return false;
        }
        synchronized (this.mDiscoveryServiceInfoSet) {
            if (!this.mDiscoveryServiceInfoSet.add(discoveryServiceInfo)) {
                return false;
            }
            ServiceListener serviceListener = new ServiceListener() { // from class: jp.konami.peerlink.nsd.NetworkServiceDiscovery.4
                @Override // javax.jmdns.ServiceListener
                public void serviceAdded(ServiceEvent serviceEvent) {
                    Logger.m967d("NetworkServiceDiscovery", "Found service: \n" + serviceEvent.toString());
                    synchronized (NetworkServiceDiscovery.this.mRegisteredServiceInfoSet) {
                        Iterator it = NetworkServiceDiscovery.this.mRegisteredServiceInfoSet.iterator();
                        while (it.hasNext()) {
                            if (((ServiceInfo) it.next()).getServiceName().equals(serviceEvent.getName())) {
                                return;
                            }
                        }
                        DiscoveryServiceInfo discoveryServiceInfo2 = new DiscoveryServiceInfo();
                        discoveryServiceInfo2.setServiceType(serviceEvent.getType());
                        synchronized (NetworkServiceDiscovery.this.mDiscoveryServiceInfoSet) {
                            if (!NetworkServiceDiscovery.this.mDiscoveryServiceInfoSet.contains(discoveryServiceInfo2)) {
                                Logger.m967d("NetworkServiceDiscovery", "Unknown service type. (service type = " + serviceEvent.getType() + ")");
                                return;
                            }
                            JmDNS dns = serviceEvent.getDNS();
                            if (dns == null) {
                                Logger.m968e("NetworkServiceDiscovery", "Unknown error.");
                            } else {
                                Logger.m967d("NetworkServiceDiscovery", "Resolving...: \n" + serviceEvent.toString());
                                dns.requestServiceInfo(serviceEvent.getType(), serviceEvent.getName(), true);
                            }
                        }
                    }
                }

                @Override // javax.jmdns.ServiceListener
                public void serviceRemoved(ServiceEvent serviceEvent) {
                    Logger.m967d("NetworkServiceDiscovery", "Lost service: \n" + serviceEvent.toString());
                    synchronized (NetworkServiceDiscovery.this.mDetectedServiceInfoMap) {
                        NetworkServiceDiscovery.this.mDetectedServiceInfoMap.remove(new AbstractMap.SimpleImmutableEntry(serviceEvent.getType(), serviceEvent.getName()));
                    }
                }

                @Override // javax.jmdns.ServiceListener
                public void serviceResolved(ServiceEvent serviceEvent) {
                    String propertyString;
                    javax.jmdns.ServiceInfo info = serviceEvent.getInfo();
                    if (info == null) {
                        Logger.m968e("NetworkServiceDiscovery", "Resolve failed: \n" + serviceEvent.toString());
                        return;
                    }
                    Logger.m967d("NetworkServiceDiscovery", "Resolved service: \n" + serviceEvent.toString());
                    DetectedServiceInfo detectedServiceInfo = new DetectedServiceInfo();
                    detectedServiceInfo.setServiceName(serviceEvent.getName());
                    detectedServiceInfo.setServiceType(serviceEvent.getType());
                    detectedServiceInfo.setHostName(info.getAddress().getHostAddress());
                    detectedServiceInfo.setPort(info.getPort());
                    Enumeration<String> propertyNames = info.getPropertyNames();
                    HashMap map = null;
                    while (propertyNames.hasMoreElements()) {
                        String strNextElement = propertyNames.nextElement();
                        if (strNextElement != null && (propertyString = info.getPropertyString(strNextElement)) != null) {
                            if (map == null) {
                                map = new HashMap();
                            }
                            map.put(strNextElement, propertyString);
                        }
                    }
                    if (map != null) {
                        detectedServiceInfo.setAttribute(map);
                    }
                    synchronized (NetworkServiceDiscovery.this.mDetectedServiceInfoMap) {
                        NetworkServiceDiscovery.this.mDetectedServiceInfoMap.put(new AbstractMap.SimpleImmutableEntry(serviceEvent.getType(), serviceEvent.getName()), detectedServiceInfo);
                    }
                }
            };
            JmDNS jmDNS = this.mJmDNS4;
            if (jmDNS != null) {
                jmDNS.addServiceListener(discoveryServiceInfo.getServiceType(), serviceListener);
            }
            JmDNS jmDNS2 = this.mJmDNS6;
            if (jmDNS2 == null) {
                return true;
            }
            jmDNS2.addServiceListener(discoveryServiceInfo.getServiceType(), serviceListener);
            return true;
        }
    }

    public boolean stopServiceDiscovery() {
        if (this.mJmDNS4 == null && this.mJmDNS6 == null) {
            return false;
        }
        synchronized (this.mDiscoveryServiceInfoSet) {
            for (DiscoveryServiceInfo discoveryServiceInfo : this.mDiscoveryServiceInfoSet) {
                ServiceListener serviceListener = new ServiceListener() { // from class: jp.konami.peerlink.nsd.NetworkServiceDiscovery.5
                    @Override // javax.jmdns.ServiceListener
                    public void serviceAdded(ServiceEvent serviceEvent) {
                    }

                    @Override // javax.jmdns.ServiceListener
                    public void serviceRemoved(ServiceEvent serviceEvent) {
                    }

                    @Override // javax.jmdns.ServiceListener
                    public void serviceResolved(ServiceEvent serviceEvent) {
                    }
                };
                JmDNS jmDNS = this.mJmDNS4;
                if (jmDNS != null) {
                    jmDNS.removeServiceListener(discoveryServiceInfo.getServiceType(), serviceListener);
                }
                JmDNS jmDNS2 = this.mJmDNS6;
                if (jmDNS2 != null) {
                    jmDNS2.removeServiceListener(discoveryServiceInfo.getServiceType(), serviceListener);
                }
            }
        }
        synchronized (this.mDiscoveryServiceInfoSet) {
            this.mDiscoveryServiceInfoSet.clear();
        }
        synchronized (this.mDetectedServiceInfoMap) {
            this.mDetectedServiceInfoMap.clear();
        }
        return true;
    }

    public boolean unregisterService() {
        if (this.mJmDNS4 == null && this.mJmDNS6 == null) {
            return false;
        }
        this.mExecutorService.execute(new Runnable() { // from class: jp.konami.peerlink.nsd.NetworkServiceDiscovery.3
            @Override // java.lang.Runnable
            public void run() {
                if (NetworkServiceDiscovery.this.mJmDNS4 != null) {
                    NetworkServiceDiscovery.this.mJmDNS4.unregisterAllServices();
                }
                if (NetworkServiceDiscovery.this.mJmDNS6 != null) {
                    NetworkServiceDiscovery.this.mJmDNS6.unregisterAllServices();
                }
                synchronized (NetworkServiceDiscovery.this.mRegisteredServiceInfoSet) {
                    NetworkServiceDiscovery.this.mRegisteredServiceInfoSet.clear();
                }
                Logger.m967d("NetworkServiceDiscovery", "Unregistered service.");
            }
        });
        return true;
    }
}
