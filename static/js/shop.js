document.addEventListener('DOMContentLoaded', () => {
  const pendingOrderBadge = document.querySelector('[data-pending-shipping-count]');
  if (pendingOrderBadge) {
    const refreshPendingOrders = async () => {
      try {
        const response = await fetch(pendingOrderBadge.dataset.countUrl, {
          credentials: 'same-origin',
          cache: 'no-store',
          headers: { Accept: 'application/json' },
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const { count } = await response.json();
        if (!Number.isInteger(count) || count < 0) throw new Error('Invalid pending order count');
        pendingOrderBadge.textContent = String(count);
        pendingOrderBadge.hidden = count === 0;
        pendingOrderBadge.setAttribute('aria-label', `Замовлень очікують відправки: ${count}`);
      } catch (error) {
        console.warn('Не вдалося оновити лічильник замовлень:', error);
      }
    };

    window.setInterval(refreshPendingOrders, 30000);
  }

  const menuToggle = document.querySelector('[data-menu-toggle]');
  const mainNavigation = document.querySelector('[data-main-navigation]');
  const mobileNavigation = window.matchMedia('(max-width: 960px)');

  if (menuToggle && mainNavigation) {
    const setMenuOpen = (open) => {
      mainNavigation.classList.toggle('is-open', open);
      mainNavigation.setAttribute('aria-hidden', String(mobileNavigation.matches && !open));
      mainNavigation.inert = mobileNavigation.matches && !open;
      menuToggle.setAttribute('aria-expanded', String(open));
      menuToggle.setAttribute('aria-label', open ? 'Закрити меню' : 'Відкрити меню');
    };

    setMenuOpen(false);
    menuToggle.addEventListener('click', () => {
      setMenuOpen(menuToggle.getAttribute('aria-expanded') !== 'true');
    });
    mainNavigation.addEventListener('click', (event) => {
      if (mobileNavigation.matches && event.target.closest('a')) setMenuOpen(false);
    });
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && mobileNavigation.matches && menuToggle.getAttribute('aria-expanded') === 'true') {
        setMenuOpen(false);
        menuToggle.focus();
      }
    });
    mobileNavigation.addEventListener('change', () => setMenuOpen(false));
  }

  const cartStorageKey = 'hathouse_cart';
  const cartDrawer = document.querySelector('[data-cart-drawer]');
  const cartBackdrop = document.querySelector('[data-cart-backdrop]');
  const cartOpenButton = document.querySelector('[data-cart-open]');
  const cartItemsElement = document.querySelector('[data-cart-items]');
  const cartCountElement = document.querySelector('[data-cart-count]');
  const cartTotalElement = document.querySelector('[data-cart-total]');
  const cartSavingsElement = document.querySelector('[data-cart-savings]');
  const cartSavingsAmountElement = document.querySelector('[data-cart-savings-amount]');
  const cartSavingsPercentElement = document.querySelector('[data-cart-savings-percent]');
  const cartCheckoutButton = document.querySelector('[data-cart-checkout]');
  const confirmDialog = document.querySelector('[data-cart-confirm]');
  const confirmMessage = document.querySelector('#cart-confirm-message');
  let pendingRemovalId = null;
  let cart = [];
  const visibleProducts = new Map(
    [...document.querySelectorAll('.add-to-cart[data-product-id]')].map((button) => {
      const { productId, productPrice, productOldPrice, productImage } = button.dataset;
      const price = Number(productPrice);
      const rawOldPrice = Number(productOldPrice);
      return [productId, {
        price,
        oldPrice: Number.isFinite(rawOldPrice) && rawOldPrice > price ? rawOldPrice : null,
        image: productImage || '',
      }];
    })
  );

  try {
    const savedCart = JSON.parse(localStorage.getItem(cartStorageKey) || '[]');
    if (Array.isArray(savedCart)) {
      cart = savedCart.filter((item) =>
        item &&
        typeof item.id === 'string' &&
        typeof item.name === 'string' &&
        Number.isFinite(item.price) &&
        item.price >= 0 &&
        Number.isInteger(item.quantity) &&
        item.quantity > 0
      ).map((item) => {
        const currentProduct = visibleProducts.get(item.id);
        return currentProduct
          ? { ...item, ...currentProduct }
          : { ...item, oldPrice: Number.isFinite(item.oldPrice) ? item.oldPrice : null };
      });
    }
  } catch (error) {
    console.warn('Не вдалося прочитати кошик із localStorage:', error);
  }

  const formatPrice = (price) => `${price.toLocaleString('uk-UA')} грн`;
  const getItemSavings = (item) =>
    Number.isFinite(item.oldPrice) && item.oldPrice > item.price ? (item.oldPrice - item.price) * item.quantity : 0;
  const saveCart = () => localStorage.setItem(cartStorageKey, JSON.stringify(cart));

  const renderCart = () => {
    const itemCount = cart.reduce((total, item) => total + item.quantity, 0);
    const total = cart.reduce((sum, item) => sum + item.price * item.quantity, 0);
    const savings = cart.reduce((sum, item) => sum + getItemSavings(item), 0);
    const originalTotal = total + savings;
    const savingsPercent = originalTotal ? Math.round((savings / originalTotal) * 100) : 0;
    cartCountElement.textContent = String(itemCount);
    cartCountElement.hidden = itemCount === 0;
    cartTotalElement.textContent = formatPrice(total);
    cartSavingsElement.hidden = savings === 0;
    cartSavingsAmountElement.textContent = formatPrice(savings);
    cartSavingsPercentElement.textContent = `(${savingsPercent}%)`;
    cartCheckoutButton.disabled = cart.length === 0;
    cartItemsElement.replaceChildren();

    if (cart.length === 0) {
      const emptyMessage = document.createElement('p');
      emptyMessage.className = 'cart-empty';
      emptyMessage.textContent = 'Ваш кошик поки порожній.';
      cartItemsElement.append(emptyMessage);
      return;
    }

    cart.forEach((item) => {
      const row = document.createElement('article');
      row.className = 'cart-item';

      const image = document.createElement('img');
      image.className = 'cart-item-image';
      image.src = item.image || '';
      image.alt = item.name;

      const details = document.createElement('div');
      details.className = 'cart-item-details';

      const heading = document.createElement('div');
      heading.className = 'cart-item-heading';

      const name = document.createElement('h3');
      name.className = 'cart-item-name';
      name.textContent = item.name;

      const remove = document.createElement('button');
      remove.type = 'button';
      remove.className = 'cart-item-remove';
      remove.textContent = '×';
      remove.title = 'Видалити товар із кошика';
      remove.setAttribute('aria-label', `Видалити ${item.name} із кошика`);
      remove.dataset.cartRemove = item.id;

      heading.append(name, remove);

      const price = document.createElement('p');
      price.className = 'cart-item-price';
      if (Number.isFinite(item.oldPrice) && item.oldPrice > item.price) {
        const oldPrice = document.createElement('del');
        oldPrice.textContent = formatPrice(item.oldPrice);

        const newPrice = document.createElement('strong');
        newPrice.textContent = formatPrice(item.price);

        const discountPercent = item.oldPrice ? Math.round(((item.oldPrice - item.price) / item.oldPrice) * 100) : 0;
        const discountBadge = document.createElement('span');
        discountBadge.className = 'discount-badge cart-discount-badge';
        discountBadge.textContent = `-${discountPercent}%`;

        price.append(oldPrice, newPrice, discountBadge);
      } else {
        price.textContent = formatPrice(item.price);
      }

      const quantityControls = document.createElement('div');
      quantityControls.className = 'cart-quantity';
      quantityControls.setAttribute('aria-label', `Кількість: ${item.quantity}`);

      const decrease = document.createElement('button');
      decrease.type = 'button';
      decrease.textContent = '−';
      decrease.setAttribute('aria-label', `Зменшити кількість: ${item.name}`);
      decrease.dataset.cartDecrease = item.id;

      const quantity = document.createElement('span');
      quantity.textContent = String(item.quantity);
      quantity.setAttribute('aria-live', 'polite');

      const increase = document.createElement('button');
      increase.type = 'button';
      increase.textContent = '+';
      increase.setAttribute('aria-label', `Збільшити кількість: ${item.name}`);
      increase.dataset.cartIncrease = item.id;

      quantityControls.append(decrease, quantity, increase);
      details.append(heading, price, quantityControls);
      row.append(image, details);
      cartItemsElement.append(row);
    });
  };

  const setDrawerOpen = (open) => {
    cartDrawer.classList.toggle('is-open', open);
    cartBackdrop.classList.toggle('is-visible', open);
    cartDrawer.setAttribute('aria-hidden', String(!open));
    cartDrawer.inert = !open;
    cartOpenButton.setAttribute('aria-expanded', String(open));
    document.body.classList.toggle('cart-open', open);
    if (open) {
      cartDrawer.querySelector('[data-cart-close]').focus();
    } else {
      cartOpenButton.focus();
    }
  };

  const closeConfirmDialog = () => {
    confirmDialog.hidden = true;
    pendingRemovalId = null;
    confirmDialog.inert = true;
  };

  const requestItemRemoval = (item) => {
    pendingRemovalId = item.id;
    confirmMessage.textContent = `Видалити «${item.name}» із кошика? Усі ${item.quantity} шт. буде видалено.`;
    confirmDialog.hidden = false;
    confirmDialog.inert = false;
    confirmDialog.querySelector('[data-cart-remove-confirm]').focus();
  };

  cartOpenButton.addEventListener('click', () => setDrawerOpen(true));
  cartDrawer.querySelector('[data-cart-close]').addEventListener('click', () => setDrawerOpen(false));
  cartBackdrop.addEventListener('click', () => setDrawerOpen(false));
  confirmDialog.querySelector('[data-cart-remove-cancel]').addEventListener('click', closeConfirmDialog);
  confirmDialog.querySelector('[data-cart-remove-confirm]').addEventListener('click', () => {
    cart = cart.filter((item) => item.id !== pendingRemovalId);
    saveCart();
    renderCart();
    closeConfirmDialog();
  });

  document.addEventListener('click', (event) => {
    const clickedElement = event.target instanceof Element ? event.target : null;
    if (!clickedElement) return;

    const checkoutButton = clickedElement.closest('[data-cart-checkout]');
    if (checkoutButton && cart.length > 0) {
      const checkoutForm = document.querySelector('[data-cart-checkout-form]');
      checkoutForm.querySelector('[data-cart-checkout-items]').value = JSON.stringify(
        cart.map((item) => ({ id: item.id, quantity: item.quantity }))
      );
      checkoutForm.requestSubmit();
      return;
    }

    const addButton = clickedElement.closest('.add-to-cart');
    if (addButton && !addButton.disabled) {
      const { productId, productName, productPrice, productOldPrice, productImage } = addButton.dataset;
      const price = Number(productPrice);
      const rawOldPrice = Number(productOldPrice);
      const oldPrice = Number.isFinite(rawOldPrice) && rawOldPrice > price ? rawOldPrice : null;
      if (!productId || !productName || !Number.isFinite(price) || price < 0) {
        console.error('Не вдалося додати товар до кошика: відсутні коректні дані товару.');
        return;
      }

      const existingItem = cart.find((item) => item.id === productId);
      if (existingItem) {
        existingItem.quantity += 1;
        existingItem.name = productName;
        existingItem.price = price;
        existingItem.oldPrice = oldPrice;
        existingItem.image = productImage || '';
      } else {
        cart.push({ id: productId, name: productName, price, oldPrice, image: productImage || '', quantity: 1 });
      }
      saveCart();
      renderCart();
      setDrawerOpen(true);
      return;
    }

    const removeButton = clickedElement.closest('[data-cart-remove]');
    if (removeButton) {
      const item = cart.find((cartItem) => cartItem.id === removeButton.dataset.cartRemove);
      if (item) requestItemRemoval(item);
      return;
    }

    const increaseButton = clickedElement.closest('[data-cart-increase]');
    if (increaseButton) {
      const item = cart.find((cartItem) => cartItem.id === increaseButton.dataset.cartIncrease);
      if (item) {
        item.quantity += 1;
        saveCart();
        renderCart();
      }
      return;
    }

    const decreaseButton = clickedElement.closest('[data-cart-decrease]');
    if (decreaseButton) {
      const item = cart.find((cartItem) => cartItem.id === decreaseButton.dataset.cartDecrease);
      if (!item) return;
      if (item.quantity === 1) {
        requestItemRemoval(item);
      } else {
        item.quantity -= 1;
        saveCart();
        renderCart();
      }
    }
  });

  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape') return;
    if (!confirmDialog.hidden) {
      closeConfirmDialog();
    } else if (cartDrawer.classList.contains('is-open')) {
      setDrawerOpen(false);
    }
  });

  renderCart();

  const detail = document.querySelector('[data-product-detail]');
  if (!detail) return;

  const mainImage = detail.querySelector('[data-main-image]');
  const modal = detail.querySelector('[data-image-modal]');
  const modalImage = detail.querySelector('[data-modal-image]');
  const thumbnails = [...detail.querySelectorAll('[data-image]')];
  const gallery = thumbnails.map((button) => button.dataset.image);
  if (!gallery.length) gallery.push(mainImage.src);

  const zoomLevel = modal.querySelector('[data-image-zoom-level]');
  const imageCounter = modal.querySelector('[data-image-counter]');
  const pointers = new Map();
  let currentIndex = 0;
  let scale = 1;
  let translateX = 0;
  let translateY = 0;
  let previousDistance = 0;
  let pointerStart = null;
  let previousFocus = null;

  const renderImage = () => {
    const imageUrl = gallery[currentIndex];
    mainImage.src = imageUrl;
    modalImage.src = imageUrl;
    thumbnails.forEach((button, index) => {
      const active = index === currentIndex;
      button.classList.toggle('active', active);
      button.querySelector('.thumb')?.classList.toggle('active', active);
      button.setAttribute('aria-current', String(active));
    });
    imageCounter.textContent = `${currentIndex + 1} / ${gallery.length}`;
  };

  const renderZoom = () => {
    modalImage.style.transform = `translate(${translateX}px, ${translateY}px) scale(${scale})`;
    zoomLevel.textContent = `${Math.round(scale * 100)}%`;
    modalImage.classList.toggle('is-zoomed', scale > 1);
  };

  const resetZoom = () => {
    scale = 1;
    translateX = 0;
    translateY = 0;
    renderZoom();
  };

  const setScale = (nextScale) => {
    scale = Math.min(4, Math.max(1, nextScale));
    if (scale === 1) {
      translateX = 0;
      translateY = 0;
    }
    renderZoom();
  };

  const closeModal = () => {
    modal.classList.add('hidden');
    modal.setAttribute('aria-hidden', 'true');
    modal.inert = true;
    document.body.classList.remove('image-modal-open');
    resetZoom();
    pointers.clear();
    if (previousFocus?.isConnected) previousFocus.focus();
  };

  const openModal = () => {
    previousFocus = document.activeElement;
    const activeThumbnail = thumbnails.findIndex((button) => button.dataset.image === mainImage.src);
    currentIndex = activeThumbnail >= 0 ? activeThumbnail : 0;
    renderImage();
    resetZoom();
    modal.classList.remove('hidden');
    modal.setAttribute('aria-hidden', 'false');
    modal.inert = false;
    document.body.classList.add('image-modal-open');
    modal.querySelector('[data-close-image]').focus();
  };

  const moveImage = (direction) => {
    currentIndex = (currentIndex + direction + gallery.length) % gallery.length;
    renderImage();
    resetZoom();
  };

  thumbnails.forEach((button, index) => {
    button.addEventListener('click', () => {
      currentIndex = index;
      renderImage();
      resetZoom();
    });
  });
  detail.querySelector('[data-open-image]').addEventListener('click', openModal);
  detail.querySelector('[data-close-image]').addEventListener('click', closeModal);
  modal.querySelector('[data-image-prev]').addEventListener('click', () => moveImage(-1));
  modal.querySelector('[data-image-next]').addEventListener('click', () => moveImage(1));
  modal.querySelector('[data-image-zoom-in]').addEventListener('click', () => setScale(scale + 0.25));
  modal.querySelector('[data-image-zoom-out]').addEventListener('click', () => setScale(scale - 0.25));
  modal.querySelector('[data-image-zoom-reset]').addEventListener('click', resetZoom);
  modal.addEventListener('wheel', (event) => {
    if (modal.classList.contains('hidden')) return;
    event.preventDefault();
    setScale(scale + (event.deltaY < 0 ? 0.2 : -0.2));
  }, { passive: false });

  modalImage.addEventListener('pointerdown', (event) => {
    modalImage.setPointerCapture(event.pointerId);
    pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
    if (pointers.size === 1) {
      pointerStart = { x: event.clientX, y: event.clientY, translateX, translateY };
    } else if (pointers.size === 2) {
      const [first, second] = [...pointers.values()];
      previousDistance = Math.hypot(first.x - second.x, first.y - second.y);
    }
  });

  modalImage.addEventListener('pointermove', (event) => {
    if (!pointers.has(event.pointerId)) return;
    pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
    if (pointers.size >= 2) {
      const [first, second] = [...pointers.values()];
      const distance = Math.hypot(first.x - second.x, first.y - second.y);
      if (previousDistance) setScale(scale * (distance / previousDistance));
      previousDistance = distance;
    } else if (scale > 1 && pointerStart) {
      translateX = pointerStart.translateX + event.clientX - pointerStart.x;
      translateY = pointerStart.translateY + event.clientY - pointerStart.y;
      renderZoom();
    }
  });

  const finishPointer = (event) => {
    const pointer = pointers.get(event.pointerId);
    if (!pointer) return;
    pointers.delete(event.pointerId);
    if (pointers.size === 0 && pointerStart) {
      const deltaX = pointer.x - pointerStart.x;
      const deltaY = pointer.y - pointerStart.y;
      if (scale === 1 && Math.abs(deltaX) > 55 && Math.abs(deltaX) > Math.abs(deltaY)) {
        moveImage(deltaX < 0 ? 1 : -1);
      } else if (scale > 1 && Math.abs(deltaX) < 8 && Math.abs(deltaY) < 8) {
        pointerStart = null;
      }
      pointerStart = null;
    } else if (pointers.size === 1) {
      const [remaining] = pointers.values();
      pointerStart = { ...remaining, translateX, translateY };
    }
    previousDistance = 0;
  };
  modalImage.addEventListener('pointerup', finishPointer);
  modalImage.addEventListener('pointercancel', finishPointer);
  modal.addEventListener('click', (event) => {
    if (event.target === modal) closeModal();
  });
  document.addEventListener('keydown', (event) => {
    if (modal.classList.contains('hidden')) return;
    if (event.key === 'Escape') {
      closeModal();
    } else if (event.key === 'ArrowRight') {
      event.preventDefault();
      moveImage(1);
    } else if (event.key === 'ArrowLeft') {
      event.preventDefault();
      moveImage(-1);
    } else if (event.key === '+' || event.key === '=') {
      setScale(scale + 0.25);
    } else if (event.key === '-') {
      setScale(scale - 0.25);
    } else if (event.key === '0') {
      resetZoom();
    } else if (event.key === 'Tab') {
      const focusable = [...modal.querySelectorAll('button:not(:disabled)')];
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
  });
});
