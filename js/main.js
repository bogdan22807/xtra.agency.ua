(function () {
  "use strict";

  const $ = (sel, ctx = document) => ctx.querySelector(sel);
  const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];

  /* Mobile menu */
  const burger = $("#burger");
  const mobileMenu = $("#mobileMenu");
  const menuOverlay = $("#menuOverlay");

  function closeMenu() {
    mobileMenu?.classList.remove("is-open");
    menuOverlay?.classList.add("hidden");
    burger?.setAttribute("aria-expanded", "false");
    document.body.style.overflow = "";
  }

  function openMenu() {
    mobileMenu?.classList.add("is-open");
    menuOverlay?.classList.remove("hidden");
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
      header?.classList.toggle("shadow-2xl", window.scrollY > 40);
      header?.classList.toggle("border-b", window.scrollY > 40);
      header?.classList.toggle("border-white/10", window.scrollY > 40);
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

  /* Counter animation */
  function animateCounter(el) {
    const target = parseFloat(el.dataset.target);
    const suffix = el.dataset.suffix || "";
    const prefix = el.dataset.prefix || "";
    const isDecimal = el.dataset.decimal === "true";
    const duration = 2000;
    const start = performance.now();

    function tick(now) {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      const value = target * eased;
      el.textContent =
        prefix +
        (isDecimal ? value.toFixed(1) : Math.floor(value).toLocaleString("uk-UA")) +
        suffix;
      if (progress < 1) requestAnimationFrame(tick);
    }

    requestAnimationFrame(tick);
  }

  const counterEls = $$(".stat-number[data-target]");
  const counterObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          animateCounter(entry.target);
          counterObserver.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.5 }
  );
  counterEls.forEach((el) => counterObserver.observe(el));

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
      dot.classList.toggle("bg-[#FFD400]", i === reviewIndex);
      dot.classList.toggle("bg-white/20", i !== reviewIndex);
    });
  }

  function buildDots() {
    if (!dotsContainer) return;
    dotsContainer.innerHTML = "";
    const max = getMaxIndex();
    for (let i = 0; i <= max; i++) {
      const dot = document.createElement("button");
      dot.className =
        "review-dot w-2.5 h-2.5 rounded-full transition-colors duration-300 " +
        (i === 0 ? "bg-[#FFD400]" : "bg-white/20");
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

  /* Auto-advance reviews */
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
    modal?.classList.remove("hidden");
    modal?.classList.add("flex");
    document.body.style.overflow = "hidden";
  }

  function closeModal() {
    modal?.classList.add("hidden");
    modal?.classList.remove("flex");
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
})();
