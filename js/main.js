(function () {
  "use strict";

  const $ = (sel, ctx = document) => ctx.querySelector(sel);
  const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];

  function initIcons() {
    if (typeof lucide !== "undefined") lucide.createIcons();
  }

  initIcons();

  /* Mobile menu */
  const burger = $("#burger");
  const mobileMenu = $("#mobileMenu");
  const menuOverlay = $("#menuOverlay");

  function closeMenu() {
    mobileMenu?.classList.remove("is-open");
    if (menuOverlay) menuOverlay.hidden = true;
    burger?.setAttribute("aria-expanded", "false");
    document.body.style.overflow = "";
  }

  function openMenu() {
    mobileMenu?.classList.add("is-open");
    if (menuOverlay) menuOverlay.hidden = false;
    burger?.setAttribute("aria-expanded", "true");
    document.body.style.overflow = "hidden";
  }

  burger?.addEventListener("click", () => {
    mobileMenu?.classList.contains("is-open") ? closeMenu() : openMenu();
  });

  menuOverlay?.addEventListener("click", closeMenu);
  $$("#mobileMenu a").forEach((link) => link.addEventListener("click", closeMenu));

  /* Header behavior on scroll */
  const header = $("#header");
  window.addEventListener(
    "scroll",
    () => {
      header?.classList.toggle("is-scrolled", window.scrollY > 40);
    },
    { passive: true }
  );

  /* Scroll reveal */
  const revealEls = $$(".reveal");
  const revealObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          revealObserver.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
  );
  revealEls.forEach((el) => revealObserver.observe(el));

  /* FAQ accordion */
  $$(".faq-item").forEach((item) => {
    const btn = $(".faq-question", item);
    btn?.addEventListener("click", () => {
      const isOpen = item.classList.contains("is-open");
      $$(".faq-item").forEach((i) => {
        i.classList.remove("is-open");
        $(".faq-question", i)?.setAttribute("aria-expanded", "false");
      });
      if (!isOpen) {
        item.classList.add("is-open");
        btn.setAttribute("aria-expanded", "true");
      }
    });
  });

  /* Reviews slider */
  const track = $("#reviewsTrack");
  const prevBtn = $("#reviewsPrev");
  const nextBtn = $("#reviewsNext");
  const dotsContainer = $("#reviewsDots");
  let reviewIndex = 0;

  function getVisibleCount() {
    if (window.innerWidth >= 1024) return 3;
    if (window.innerWidth >= 768) return 2;
    return 1;
  }

  function getMaxIndex() {
    const cards = $$(".review-card", track);
    return Math.max(0, cards.length - getVisibleCount());
  }

  function updateCarousel() {
    if (!track) return;
    const cards = $$(".review-card", track);
    if (!cards.length) return;
    const gap = 24;
    const cardWidth = cards[0].offsetWidth + gap;
    track.style.transform = `translateX(-${reviewIndex * cardWidth}px)`;
    $$(".review-dot").forEach((dot, i) => {
      dot.classList.toggle("is-active", i === reviewIndex);
    });
  }

  function buildDots() {
    if (!dotsContainer) return;
    dotsContainer.innerHTML = "";
    const max = getMaxIndex();
    for (let i = 0; i <= max; i++) {
      const dot = document.createElement("button");
      dot.className = "review-dot" + (i === 0 ? " is-active" : "");
      dot.setAttribute("aria-label", `Відгук ${i + 1}`);
      dot.addEventListener("click", () => {
        reviewIndex = i;
        updateCarousel();
      });
      dotsContainer.appendChild(dot);
    }
  }

  prevBtn?.addEventListener("click", () => {
    reviewIndex = reviewIndex <= 0 ? getMaxIndex() : reviewIndex - 1;
    updateCarousel();
  });

  nextBtn?.addEventListener("click", () => {
    reviewIndex = reviewIndex >= getMaxIndex() ? 0 : reviewIndex + 1;
    updateCarousel();
  });

  buildDots();
  updateCarousel();
  window.addEventListener("resize", () => {
    reviewIndex = Math.min(reviewIndex, getMaxIndex());
    buildDots();
    updateCarousel();
  });

  setInterval(() => {
    if (getMaxIndex() === 0) return;
    reviewIndex = reviewIndex >= getMaxIndex() ? 0 : reviewIndex + 1;
    updateCarousel();
  }, 6000);

  /* Consult modal */
  const modal = $("#consultModal");
  const openBtns = $$("[data-open-consult]");
  const closeBtns = $$("[data-close-consult]");

  function openModal() {
    if (modal) modal.hidden = false;
    document.body.style.overflow = "hidden";
    initIcons();
  }

  function closeModal() {
    if (modal) modal.hidden = true;
    document.body.style.overflow = "";
  }

  openBtns.forEach((btn) => btn.addEventListener("click", openModal));
  closeBtns.forEach((btn) => btn.addEventListener("click", closeModal));
  modal?.addEventListener("click", (e) => {
    if (e.target === modal) closeModal();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      closeMenu();
      closeModal();
    }
  });

  $("#consultForm")?.addEventListener("submit", (e) => {
    e.preventDefault();
    const form = e.target;
    const name = form.name.value.trim();
    const phone = form.phone.value.trim();
    if (!name || !phone) {
      alert("Заповніть імʼя та телефон");
      return;
    }
    alert("Дякуємо! Ми звʼяжемося з вами найближчим часом.");
    form.reset();
    closeModal();
  });

  /* Configurator choices */
  $$("#siteConfigurator [data-choice-group]").forEach((group) => {
    const buttons = $$("[data-choice]", group);
    buttons.forEach((button) => {
      button.addEventListener("click", () => {
        buttons.forEach((item) => item.classList.remove("is-selected"));
        button.classList.add("is-selected");
        const input = group.nextElementSibling;
        if (input?.tagName === "INPUT") input.value = button.dataset.choice || "";
      });
    });
  });

  $("#siteConfigurator")?.addEventListener("submit", (e) => {
    e.preventDefault();
    openModal();
  });

  /* Phone sleep, dimming, phone vs PC */
  const deviceLab = $("#deviceLab");
  if (deviceLab) {
    const CASES = {
      coffee: {
        label: "Кава",
        kind: "photo",
        phone: "assets/devices/coffee.webp",
        phoneAlt: "Сайт кавʼярні на екрані телефону",
        desktop: "assets/mockup-business.svg",
        desktopAlt: "Десктопна версія сайту кавʼярні",
        url: "pricedrop.ua",
      },
      clothes: {
        label: "Одяг",
        kind: "photo",
        phone: "assets/devices/clothes.webp",
        phoneAlt: "Інтернет-магазин одягу на телефоні",
        desktop: "assets/mockup-ecommerce.svg",
        desktopAlt: "Десктопна версія інтернет-магазину",
        url: "chloe.shop",
      },
      realty: {
        label: "Нерухомість",
        kind: "photo",
        phone: "assets/devices/realty.webp",
        phoneAlt: "Сайт нерухомості на телефоні",
        desktop: "assets/mockup-corporate.svg",
        desktopAlt: "Десктопна версія сайту нерухомості",
        url: "ulfry.com",
      },
      landing: {
        label: "Агенція",
        kind: "screen",
        phone: "assets/mockup-landing.svg",
        phoneAlt: "Лендинг агенції на телефоні",
        desktop: "assets/mockup-landing.svg",
        desktopAlt: "Лендинг агенції на компʼютері",
        url: "xtra.agency",
      },
      interior: {
        label: "Інтерʼєр",
        kind: "photo",
        phone: "assets/devices/interior.webp",
        phoneAlt: "Сайт інтерʼєру на телефоні",
        desktop: "assets/mockup-webapp.svg",
        desktopAlt: "Десктопна версія сайту інтерʼєру",
        url: "feather.design",
      },
      tours: {
        label: "Тури",
        kind: "photo",
        phone: "assets/devices/tours.webp",
        phoneAlt: "Сервіс турів на телефоні",
        desktop: "assets/mockup-saas.svg",
        desktopAlt: "Десктопна версія сервісу турів",
        url: "trvl.app",
      },
      analytics: {
        label: "Аналітика",
        kind: "photo",
        phone: "assets/devices/analytics.webp",
        phoneAlt: "Аналітична платформа на телефоні",
        desktop: "assets/mockup-crm.svg",
        desktopAlt: "Десктопна версія аналітичної платформи",
        url: "spaatz.app",
      },
      nft: {
        label: "NFT",
        kind: "photo",
        phone: "assets/devices/nft.webp",
        phoneAlt: "NFT-маркетплейс на телефоні",
        desktop: "assets/mockup-personal.svg",
        desktopAlt: "Десктопний макет цифрової платформи",
        url: "nft.market",
      },
    };

    const caseRow = $(".device-lab__cases", deviceLab);
    const phonePhotoWrap = $("#phonePhotoWrap");
    const phoneCssWrap = $("#phoneCssWrap");
    const phoneImg = $("#devicePhoneImg");
    const phoneScreen = $("#devicePhoneScreen");
    const pcImg = $("#devicePcImg");
    const urlEl = $("#deviceUrl");
    const sleepBtn = $("#deviceSleep");
    const sleepLabel = $("span", sleepBtn);
    const dimInput = $("#deviceDim");
    const dimValue = $("#deviceDimValue");
    const statusEl = $("#deviceStatus");
    const modeButtons = $$("[data-device-mode]", deviceLab);

    let caseId = "coffee";
    let mode = "phone";
    let asleep = false;

    Object.entries(CASES).forEach(([id, item]) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "device-chip" + (id === caseId ? " is-selected" : "");
      button.dataset.caseId = id;
      button.setAttribute("role", "tab");
      button.textContent = item.label;
      button.addEventListener("click", () => selectCase(id));
      caseRow.appendChild(button);
    });

    function paintClock() {
      const now = new Date();
      const time = now.toLocaleTimeString("uk-UA", { hour: "2-digit", minute: "2-digit" });
      const date = now.toLocaleDateString("uk-UA", { weekday: "long", day: "numeric", month: "long" });
      $$(".device-clock", deviceLab).forEach((el) => {
        el.textContent = time;
      });
      $$(".device-date", deviceLab).forEach((el) => {
        el.textContent = date;
      });
    }

    function selectCase(id) {
      if (!CASES[id]) return;
      caseId = id;
      const item = CASES[id];
      $$(".device-chip", deviceLab).forEach((chip) => {
        const on = chip.dataset.caseId === id;
        chip.classList.toggle("is-selected", on);
        chip.setAttribute("aria-selected", on ? "true" : "false");
      });
      const photo = item.kind === "photo";
      phonePhotoWrap.hidden = !photo;
      phoneCssWrap.hidden = photo;
      if (photo) {
        phoneImg.src = item.phone;
        phoneImg.alt = item.phoneAlt;
      } else {
        phoneScreen.src = item.phone;
        phoneScreen.alt = item.phoneAlt;
      }
      pcImg.src = item.desktop;
      pcImg.alt = item.desktopAlt;
      urlEl.textContent = item.url;
    }

    function setMode(next) {
      mode = next;
      deviceLab.dataset.mode = next;
      modeButtons.forEach((button) => {
        const on = button.dataset.deviceMode === next;
        button.classList.toggle("is-selected", on);
        button.setAttribute("aria-selected", on ? "true" : "false");
      });
    }

    function renderState() {
      deviceLab.classList.toggle("is-asleep", asleep);
      sleepBtn.classList.toggle("is-active", asleep);
      sleepBtn.setAttribute("aria-pressed", asleep ? "true" : "false");
      if (sleepLabel) sleepLabel.textContent = asleep ? "Розбудити телефон" : "Сон на телефоні";
      const dim = Number(dimInput.value);
      deviceLab.style.setProperty("--dim", String(dim));
      deviceLab.style.setProperty("--dim-fill", String((dim / Number(dimInput.max)) * 100));
      dimValue.textContent = dim + "%";
      dimInput.setAttribute("aria-valuenow", String(dim));
      const sleepText = asleep ? "Телефон спить." : "Екран телефону увімкнено.";
      const where =
        mode === "both" ? " Порівняння: телефон проти ПК." : mode === "pc" ? " Зараз показано ПК." : " Зараз показано телефон.";
      statusEl.textContent = sleepText + " Затемнення " + dim + "% діє на телефон і на ПК." + where;
    }

    modeButtons.forEach((button) => {
      button.addEventListener("click", () => {
        setMode(button.dataset.deviceMode);
        renderState();
      });
    });

    sleepBtn.addEventListener("click", () => {
      asleep = !asleep;
      if (asleep && mode === "pc") setMode("both");
      renderState();
    });

    $$(".js-wake", deviceLab).forEach((button) => {
      button.addEventListener("click", () => {
        asleep = false;
        renderState();
      });
    });

    dimInput.addEventListener("input", renderState);

    $$("[data-device-case]").forEach((link) => {
      link.addEventListener("click", () => selectCase(link.dataset.deviceCase));
    });

    paintClock();
    setInterval(paintClock, 1000);
    selectCase(caseId);
    renderState();
  }
})();
