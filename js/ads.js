(function () {
    var config = {
        enabled: true,
        placeholders: false,
        // 广告单元配置 - 在Google AdSense后台创建广告单元后填入
        // 每个广告位对应一个AdSense广告单元ID
        slots: {
            "top-banner": {
                label: "AD",
                html: ""
                // AdSense示例: html: '<ins class="adsbygoogle" style="display:block;width:320px;height:50px" data-ad-client="ca-pub-5678257058574392" data-ad-slot="YOUR_SLOT_ID"></ins>'
            },
            "bottom-banner": {
                label: "AD",
                html: ""
                // AdSense示例: html: '<ins class="adsbygoogle" style="display:inline-block;width:160px;height:50px" data-ad-client="ca-pub-5678257058574392" data-ad-slot="YOUR_SLOT_ID"></ins>'
            },
            "right-float": {
                label: "AD",
                html: ""
                // AdSense示例: html: '<ins class="adsbygoogle" style="display:inline-block;width:100px;height:200px" data-ad-client="ca-pub-5678257058574392" data-ad-slot="YOUR_SLOT_ID"></ins>'
            },
            "pause-interstitial": {
                label: "AD",
                html: ""
                // 暂停弹窗广告 - 建议使用较大的广告单元
                // AdSense示例: html: '<ins class="adsbygoogle" style="display:block;width:280px;height:200px" data-ad-client="ca-pub-5678257058574392" data-ad-slot="YOUR_SLOT_ID"></ins>'
            }
        }
    };

    function renderSlot(element) {
        var slotName = element.getAttribute("data-ad-slot");
        var slot = config.slots[slotName];
        if (!config.enabled || !slot) {
            return;
        }

        if (slot.html) {
            element.innerHTML = slot.html;
            element.className += " is-visible";
            // 如果是AdSense代码，尝试推送广告
            try {
                if (window.adsbygoogle && slot.html.indexOf('adsbygoogle') !== -1) {
                    (adsbygoogle = window.adsbygoogle || []).push({});
                }
            } catch(e) {}
            return;
        }

        if (config.placeholders) {
            element.innerHTML = slot.label || "AD";
            element.className += " is-visible";
        }
    }

    function bootAds() {
        var slots = document.querySelectorAll("[data-ad-slot]");
        for (var i = 0; i < slots.length; i += 1) {
            renderSlot(slots[i]);
        }
    }

    // 广告收入追踪
    window.GameAdStats = {
        impressions: 0,
        slotViews: {},
        trackImpression: function(slotName) {
            this.impressions++;
            this.slotViews[slotName] = (this.slotViews[slotName] || 0) + 1;
            console.log('[AdStat] ' + slotName + ' shown. Total: ' + this.impressions);
        },
        getStats: function() {
            return {
                totalImpressions: this.impressions,
                slotBreakdown: this.slotViews
            };
        }
    };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", bootAds);
    } else {
        bootAds();
    }

    window.GameAdConfig = config;
}());
