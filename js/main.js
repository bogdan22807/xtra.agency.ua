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
})();
