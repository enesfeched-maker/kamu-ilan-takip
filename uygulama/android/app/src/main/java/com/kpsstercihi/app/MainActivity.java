package com.kpsstercihi.app;

import android.os.Bundle;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebView;
import com.getcapacitor.BridgeActivity;
import com.getcapacitor.BridgeWebViewClient;
import java.io.ByteArrayInputStream;

public class MainActivity extends BridgeActivity {

    /** AdSense uygulama içi WebView'da gösterilmez; uygulamada reklam yalnız AdMob ile olur. */
    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        bridge.setWebViewClient(new BridgeWebViewClient(bridge) {
            @Override
            public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                if ("pagead2.googlesyndication.com".equals(request.getUrl().getHost())) {
                    return new WebResourceResponse("text/javascript", "utf-8", new ByteArrayInputStream(new byte[0]));
                }
                return super.shouldInterceptRequest(view, request);
            }
        });
    }
}