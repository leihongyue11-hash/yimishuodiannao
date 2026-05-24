(function () {
    var config = {
        enabled: true,
        placeholders: false,
        slots: {
            "top-banner": {
                label: "AD",
                html: ""
            },
            "bottom-banner": {
                label: "AD",
                html: ""
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

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", bootAds);
    } else {
        bootAds();
    }

    window.GameAdConfig = config;
}());
