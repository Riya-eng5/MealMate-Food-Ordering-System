import React, { useEffect, useMemo, useState } from 'react';
  
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function api(path, token, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;
  if (options.body && !(options.body instanceof FormData)) headers['Content-Type'] = 'application/json';
  const response = await fetch(`${API_URL}${path}`, { ...options, headers });
  const data = response.status === 204 ? null : await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = data?.detail;
    throw new Error(Array.isArray(detail) ? detail.map((x) => x.msg).join(', ') : (detail || 'Something went wrong'));
  }
  return data;
}

function money(value) {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(value || 0);
}

function App() {
  const [session, setSession] = useState(() => {
    try { return JSON.parse(localStorage.getItem('mealmate_session')) || null; } catch { return null; }
  });
  const [toast, setToast] = useState('');
  const [tab, setTab] = useState('home');

  const notify = (message) => {
    setToast(message);
    window.setTimeout(() => setToast(''), 3500);
  };

  function onLogin(data) {
    const next = { token: data.access_token, user: data.user };
    localStorage.setItem('mealmate_session', JSON.stringify(next));
    setSession(next);
    setTab('home');
  }

  function logout() {
    localStorage.removeItem('mealmate_session');
    setSession(null);
    setTab('home');
  }

  if (!session?.token || !session?.user) {
    return <AuthScreen onLogin={onLogin} notify={notify} />;
  }

  const roleTabs = {
    customer: [{ id: 'home', label: 'Discover' }, { id: 'orders', label: 'My orders' }],
    owner: [{ id: 'home', label: 'Restaurant' }, { id: 'orders', label: 'Orders' }],
    delivery: [{ id: 'home', label: 'My deliveries' }],
    admin: [{ id: 'home', label: 'Overview' }, { id: 'orders', label: 'All orders' }],
  };

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="#top" onClick={(e) => { e.preventDefault(); setTab('home'); }}>
          <span className="brand-icon">M</span><span>Meal<span className="brand-accent">Mate</span><small>FOOD, MADE SIMPLE</small></span>
        </a>
        <div className="topbar-right">
          <div className="user-chip"><span className="avatar">{session.user.name?.[0]?.toUpperCase() || 'U'}</span><span><b>{session.user.name}</b><small>{session.user.role}</small></span></div>
          <button className="btn btn-outline btn-small" onClick={logout}>Sign out</button>
        </div>
      </header>
      <main className="main-wrap">
        <div className="welcome-row">
          <div><p className="eyebrow">{new Date().toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long' })}</p><h1>{greeting(session.user.role)}</h1><p className="muted">{subGreeting(session.user.role)}</p></div>
          <span className="role-pill">{session.user.role} account</span>
        </div>
        <nav className="tabs" aria-label="Dashboard navigation">
          {(roleTabs[session.user.role] || roleTabs.customer).map((item) => <button key={item.id} className={tab === item.id ? 'tab active' : 'tab'} onClick={() => setTab(item.id)}>{item.label}</button>)}
        </nav>
        {session.user.role === 'customer' && <CustomerDashboard token={session.token} user={session.user} tab={tab} notify={notify} />}
        {session.user.role === 'owner' && <OwnerDashboard token={session.token} tab={tab} notify={notify} />}
        {session.user.role === 'delivery' && <DeliveryDashboard token={session.token} notify={notify} />}
        {session.user.role === 'admin' && <AdminDashboard token={session.token} tab={tab} notify={notify} />}
      </main>
      <footer className="footer">MealMate · Online Food Ordering & Restaurant Management System</footer>
      {toast && <div className="toast" role="status">{toast}</div>}
    </div>
  );
}

function greeting(role) {
  return ({ customer: 'What are you craving today?', owner: 'Your restaurant, at a glance.', delivery: 'Your delivery workspace.', admin: 'Platform overview.' })[role] || 'Welcome to MealMate.';
}
function subGreeting(role) {
  return ({ customer: 'Find something delicious from restaurants near you.', owner: 'Manage your menu and keep every order moving.', delivery: 'View assigned orders and update delivery progress.', admin: 'Monitor users, restaurants and incoming orders.' })[role] || '';
}

function AuthScreen({ onLogin, notify }) {
  const [mode, setMode] = useState('login');
  const [form, setForm] = useState({ name: '', email: '', password: '', address: '' });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [showDemos, setShowDemos] = useState(false);

  async function submit(e) {
    e.preventDefault(); setError(''); setBusy(true);
    try {
      if (mode === 'register') {
        await api('/auth/register', null, { method: 'POST', body: JSON.stringify(form) });
        notify('Account created. Please sign in.');
        setMode('login');
      } else {
        const result = await api('/auth/login', null, { method: 'POST', body: JSON.stringify({ email: form.email, password: form.password }) });
        onLogin(result);
      }
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }

  async function demoLogin(email) {
    setError(''); setBusy(true);
    try {
      const result = await api('/auth/login', null, { method: 'POST', body: JSON.stringify({ email, password: 'demo12345' }) });
      onLogin(result);
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }

  return (
    <div className="auth-layout">
      <section className="auth-art">
        <div className="auth-logo"><span className="brand-icon">M</span><span>Meal<span className="brand-accent">Mate</span></span></div>
        <div className="art-copy"><span className="eyebrow light">GOOD FOOD. GOOD MOOD.</span><h1>Every craving<br />has a home.</h1><p>Discover local favourites, order in a few clicks, and follow every delivery along the way.</p><div className="food-emoji">🥗 🍕 🍜</div></div>
        <div className="art-bottom">A simple food ordering experience</div>
      </section>
      <section className="auth-panel">
        <div className="auth-card">
          <span className="eyebrow">WELCOME TO MEALMATE</span>
          <h2>{mode === 'login' ? 'Sign in to continue' : 'Create your account'}</h2>
          <p className="muted">{mode === 'login' ? 'Use your account details to open your dashboard.' : 'Customer accounts can browse and place orders.'}</p>
          <form onSubmit={submit} className="form-stack">
            {mode === 'register' && <><label>Full name<input required minLength="2" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Your name" /></label><label>Delivery address<input value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} placeholder="Area, city" /></label></>}
            <label>Email address<input required type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="you@example.com" /></label>
            <label>Password<input required type="password" minLength="6" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} placeholder="At least 6 characters" /></label>
            {error && <div className="error-box">{error}</div>}
            <button className="btn btn-primary btn-wide" disabled={busy}>{busy ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Create account'}</button>
          </form>
          <p className="switch-auth">{mode === 'login' ? 'New to MealMate?' : 'Already have an account?'} <button onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError(''); }}>{mode === 'login' ? 'Create an account' : 'Sign in'}</button></p>
          <div className="demo-area"><button className="demo-toggle" onClick={() => setShowDemos(!showDemos)}>{showDemos ? 'Hide' : 'Show'} evaluator demo accounts <span>⌄</span></button>
            {showDemos && <div className="demo-grid">{[['Customer', 'customer@example.com'], ['Owner', 'owner@example.com'], ['Delivery', 'delivery@example.com'], ['Admin', 'admin@example.com']].map(([label, email]) => <button key={email} onClick={() => demoLogin(email)} disabled={busy}><b>{label}</b><small>{email}</small></button>)}<p>Demo password: <b>demo12345</b></p></div>}
          </div>
        </div>
      </section>
    </div>
  );
}

function CustomerDashboard({ token, user, tab, notify }) {
  const [restaurants, setRestaurants] = useState([]);
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState(null);
  const [menu, setMenu] = useState([]);
  const [cart, setCart] = useState([]);
  const [orders, setOrders] = useState([]);
  const [address, setAddress] = useState(user.address || '');
  const [busy, setBusy] = useState(false);
  const [reviewText, setReviewText] = useState({});

  async function loadRestaurants() {
    try { setRestaurants(await api(`/restaurants?q=${encodeURIComponent(search)}&page=1&page_size=20`, token)); }
    catch (err) { notify(err.message); }
  }
  async function loadOrders() {
    try { setOrders(await api('/orders', token)); } catch (err) { notify(err.message); }
  }
  useEffect(() => { loadRestaurants(); }, [search]);
  useEffect(() => { loadOrders(); }, []);

  async function openRestaurant(restaurant) {
    setSelected(restaurant); setCart([]);
    try { setMenu(await api(`/restaurants/${restaurant.id}/menu`, token)); }
    catch (err) { notify(err.message); }
  }
  function addToCart(item) {
    setCart((current) => {
      const found = current.find((x) => x.id === item.id);
      return found ? current.map((x) => x.id === item.id ? { ...x, quantity: x.quantity + 1 } : x) : [...current, { ...item, quantity: 1 }];
    });
  }
  function changeQuantity(id, delta) {
    setCart((current) => current.map((x) => x.id === id ? { ...x, quantity: x.quantity + delta } : x).filter((x) => x.quantity > 0));
  }
  const cartTotal = cart.reduce((sum, item) => sum + item.price * item.quantity, 0);

  async function checkout() {
    if (!cart.length || !selected) return;
    if (address.trim().length < 5) { notify('Please enter a complete delivery address.'); return; }
    setBusy(true);
    try {
      const order = await api('/orders', token, { method: 'POST', body: JSON.stringify({ restaurant_id: selected.id, delivery_address: address, items: cart.map((x) => ({ menu_item_id: x.id, quantity: x.quantity })) }) });
      await api(`/orders/${order.id}/pay`, token, { method: 'POST' });
      setCart([]); setSelected(null); await loadOrders();
      notify(`Order #${order.id} placed. Mock payment successful!`);
    } catch (err) { notify(err.message); }
    finally { setBusy(false); }
  }

  async function submitReview(orderId) {
    const draft = reviewText[orderId] || { rating: 5, comment: '' };
    try {
      await api(`/orders/${orderId}/reviews`, token, { method: 'POST', body: JSON.stringify(draft) });
      notify('Thanks for sharing your review!');
      loadOrders();
    } catch (err) { notify(err.message); }
  }

  if (tab === 'orders') return <section className="section-block"><div className="section-heading"><div><span className="eyebrow">ORDER HISTORY</span><h2>Your orders</h2></div><button className="btn btn-outline btn-small" onClick={loadOrders}>Refresh</button></div>
    {orders.length === 0 ? <EmptyState title="No orders yet" text="Your orders will appear here after checkout." /> : <div className="order-list">{orders.map((order) => <article className="order-card" key={order.id}><div className="order-top"><div><b>Order #{order.id}</b><small>{new Date(order.created_at).toLocaleString()}</small></div><span className={`status status-${order.status}`}>{pretty(order.status)}</span></div><div className="order-lines">{order.items.map((item) => <span key={item.id}>{item.quantity} × {item.item_name}</span>)}</div><div className="order-bottom"><span className="muted">Payment: {pretty(order.payment_status)} · {order.delivery_address}</span><b>{money(order.total_amount)}</b></div>
      {order.status === 'delivered' && <div className="review-form"><b>Rate this order</b><select value={reviewText[order.id]?.rating ?? 5} onChange={(e) => setReviewText({ ...reviewText, [order.id]: { ...(reviewText[order.id] || { comment: '' }), rating: Number(e.target.value) } })}><option value="5">★★★★★ · Excellent</option><option value="4">★★★★ · Good</option><option value="3">★★★ · Okay</option><option value="2">★★ · Poor</option><option value="1">★ · Bad</option></select><input placeholder="Write a short review" value={reviewText[order.id]?.comment ?? ''} onChange={(e) => setReviewText({ ...reviewText, [order.id]: { ...(reviewText[order.id] || { rating: 5 }), comment: e.target.value } })} /><button className="btn btn-primary btn-small" onClick={() => submitReview(order.id)}>Submit review</button></div>}
    </article>)}</div>}
  </section>;

  return <div className="customer-layout">
    <section className="discover-area">
      <div className="search-box"><span>⌕</span><input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search restaurants or cuisines…" /><kbd>SEARCH</kbd></div>
      {selected ? <>
        <button className="back-link" onClick={() => { setSelected(null); setCart([]); }}>← All restaurants</button>
        <div className="restaurant-banner"><div><span className="food-stamp">🍽️</span></div><div><span className="eyebrow">{selected.cuisine}</span><h2>{selected.name}</h2><p>{selected.description || 'Fresh food, made with care.'}</p><small>⌖ {selected.address}</small></div></div>
        <div className="section-heading menu-title"><div><span className="eyebrow">MADE FRESH</span><h2>Explore the menu</h2></div><span className="muted">{menu.length} items</span></div>
        <div className="menu-grid">{menu.map((item) => <article className="menu-card" key={item.id}><div className="menu-art">{item.category.toLowerCase().includes('rice') ? '🍚' : item.category.toLowerCase().includes('side') ? '🍟' : '🍛'}</div><div className="menu-info"><span className="eyebrow">{item.category}</span><h3>{item.name}</h3><p>{item.description}</p><div className="menu-card-bottom"><b>{money(item.price)}</b><button className="add-btn" onClick={() => addToCart(item)}>+ Add</button></div></div></article>)}</div>
      </> : <>
        <div className="hero-strip"><div><span className="eyebrow light">YOUR NEXT GREAT MEAL</span><h2>Good food is<br />always a good idea.</h2><p>Find your favourite flavour today.</p></div><div className="hero-food">🍲</div></div>
        <div className="section-heading"><div><span className="eyebrow">HANDPICKED FOR YOU</span><h2>Restaurants</h2></div><span className="muted">{restaurants.length} found</span></div>
        {restaurants.length === 0 ? <EmptyState title="No restaurants found" text="Try a different search term." /> : <div className="restaurant-grid">{restaurants.map((r, i) => <button className="restaurant-card" key={r.id} onClick={() => openRestaurant(r)}><div className={`restaurant-art art-${i % 4}`}><span>{['🍛', '🥘', '🍜', '🥗'][i % 4]}</span><small>{r.cuisine}</small></div><div className="restaurant-card-info"><h3>{r.name}</h3><p>{r.description || 'Fresh meals for every mood.'}</p><div><span>⌖ {r.address}</span><b>View menu →</b></div></div></button>)}</div>}
      </>}
    </section>
    <aside className="cart-panel"><div className="cart-head"><span className="cart-icon">🛍️</span><div><h3>Your basket</h3><small>{cart.reduce((sum, x) => sum + x.quantity, 0)} items</small></div></div>
      {!selected && <p className="cart-hint">Choose a restaurant to add your favourite dishes.</p>}
      {selected && cart.length === 0 && <p className="cart-hint">Your basket is empty. Add something delicious!</p>}
      {selected && cart.length > 0 && <><p className="cart-restaurant">From {selected.name}</p><div className="cart-lines">{cart.map((item) => <div className="cart-line" key={item.id}><div><b>{item.name}</b><small>{money(item.price)} each</small></div><div className="quantity"><button onClick={() => changeQuantity(item.id, -1)} aria-label="Decrease quantity">−</button><b>{item.quantity}</b><button onClick={() => changeQuantity(item.id, 1)} aria-label="Increase quantity">+</button></div></div>)}</div><label className="address-label">Delivery address<textarea rows="2" value={address} onChange={(e) => setAddress(e.target.value)} placeholder="Enter full delivery address" /></label><div className="bill-row"><span>Item total</span><b>{money(cartTotal)}</b></div><div className="bill-row"><span>Delivery fee</span><b>{money(0)}</b></div><div className="bill-total"><span>Total</span><b>{money(cartTotal)}</b></div><button className="btn btn-primary btn-wide" disabled={busy} onClick={checkout}>{busy ? 'Placing order…' : 'Place order · ' + money(cartTotal)}</button><p className="tiny-note">Mock payment is used for this demo. No real charge is made.</p></>}
    </aside>
  </div>;
}

function OwnerDashboard({ token, tab, notify }) {
  const [restaurant, setRestaurant] = useState(null);
  const [menu, setMenu] = useState([]);
  const [orders, setOrders] = useState([]);
  const [form, setForm] = useState({ name: '', description: '', category: 'Main Course', price: '' });
  const [busy, setBusy] = useState(false);

  async function load() {
    try {
      const r = await api('/owner/restaurant', token); setRestaurant(r);
      const [m, o] = await Promise.all([api('/owner/menu', token), api('/owner/orders', token)]); setMenu(m); setOrders(o);
    } catch (err) { notify(err.message); }
  }
  useEffect(() => { load(); }, []);

  async function addItem(e) {
    e.preventDefault(); setBusy(true);
    try { await api('/owner/menu', token, { method: 'POST', body: JSON.stringify({ ...form, price: Number(form.price) }) }); setForm({ name: '', description: '', category: 'Main Course', price: '' }); await load(); notify('Menu item added.'); }
    catch (err) { notify(err.message); } finally { setBusy(false); }
  }
  async function toggleItem(item) {
    try { await api(`/owner/menu/${item.id}`, token, { method: 'PATCH', body: JSON.stringify({ is_available: !item.is_available }) }); await load(); }
    catch (err) { notify(err.message); }
  }
  async function setStatus(order, status) {
    try { await api(`/owner/orders/${order.id}/status`, token, { method: 'PATCH', body: JSON.stringify({ status }) }); await load(); notify(`Order #${order.id} updated.`); }
    catch (err) { notify(err.message); }
  }

  if (tab === 'orders') return <section className="section-block"><div className="section-heading"><div><span className="eyebrow">KITCHEN QUEUE</span><h2>Incoming orders</h2></div><button className="btn btn-outline btn-small" onClick={load}>Refresh</button></div>{orders.length === 0 ? <EmptyState title="No incoming orders" text="New customer orders will show up here." /> : <div className="order-list">{orders.map((order) => <article className="order-card" key={order.id}><div className="order-top"><div><b>Order #{order.id}</b><small>{new Date(order.created_at).toLocaleString()}</small></div><span className={`status status-${order.status}`}>{pretty(order.status)}</span></div><div className="order-lines">{order.items.map((x) => <span key={x.id}>{x.quantity} × {x.item_name}</span>)}</div><div className="order-bottom"><span className="muted">Delivery: {order.delivery_address} · Payment: {pretty(order.payment_status)}</span><b>{money(order.total_amount)}</b></div><div className="card-actions">{order.status === 'pending' && <button className="btn btn-primary btn-small" onClick={() => setStatus(order, 'confirmed')}>Accept order</button>}{order.status === 'confirmed' && <button className="btn btn-primary btn-small" onClick={() => setStatus(order, 'preparing')}>Start preparing</button>}{!['cancelled', 'delivered', 'out_for_delivery'].includes(order.status) && <button className="btn btn-outline btn-small" onClick={() => setStatus(order, 'cancelled')}>Cancel</button>}</div></article>)}</div>}</section>;

  return <div className="owner-layout"><section className="owner-main"><div className="profile-card"><div className="profile-mark">🍴</div><div><span className="eyebrow">YOUR RESTAURANT</span><h2>{restaurant?.name || 'Restaurant'}</h2><p>{restaurant?.description}</p><small>⌖ {restaurant?.address} · {restaurant?.cuisine}</small></div><span className="status status-delivered">Active</span></div>
    <div className="section-heading"><div><span className="eyebrow">MENU MANAGEMENT</span><h2>Your menu</h2></div><span className="muted">{menu.length} items</span></div>
    <div className="owner-menu-list">{menu.map((item) => <div className="owner-menu-item" key={item.id}><div className="mini-food">🍽️</div><div className="grow"><b>{item.name}</b><small>{item.category} · {money(item.price)}</small></div><span className={item.is_available ? 'availability on' : 'availability off'}>{item.is_available ? 'Available' : 'Hidden'}</span><button className="btn btn-outline btn-small" onClick={() => toggleItem(item)}>{item.is_available ? 'Hide' : 'Show'}</button></div>)}</div>
    </section><aside className="form-card"><span className="eyebrow">ADD A DISH</span><h3>New menu item</h3><form className="form-stack" onSubmit={addItem}><label>Dish name<input required minLength="2" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g. Classic Veg Burger" /></label><label>Description<input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="A short description" /></label><label>Category<select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}><option>Main Course</option><option>Starter</option><option>Rice</option><option>Beverage</option><option>Dessert</option><option>Sides</option></select></label><label>Price (₹)<input required type="number" min="1" step="1" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} placeholder="150" /></label><button className="btn btn-primary btn-wide" disabled={busy}>{busy ? 'Saving…' : 'Add to menu'}</button></form><div className="tip-box">Tip: Keep dish names and descriptions clear so customers can choose quickly.</div></aside></div>;
}

function DeliveryDashboard({ token, notify }) {
  const [orders, setOrders] = useState([]);
  async function load() { try { setOrders(await api('/delivery/orders', token)); } catch (err) { notify(err.message); } }
  useEffect(() => { load(); }, []);
  async function update(order, status) {
    try { await api(`/delivery/orders/${order.id}/status`, token, { method: 'PATCH', body: JSON.stringify({ status }) }); await load(); notify(`Order #${order.id} updated.`); }
    catch (err) { notify(err.message); }
  }
  return <section className="section-block"><div className="section-heading"><div><span className="eyebrow">ASSIGNED TO YOU</span><h2>Delivery orders</h2></div><button className="btn btn-outline btn-small" onClick={load}>Refresh</button></div>{orders.length === 0 ? <EmptyState title="Nothing assigned yet" text="When the admin assigns an order to you, it will appear here." /> : <div className="delivery-grid">{orders.map((order) => <article className="delivery-card" key={order.id}><div className="delivery-card-top"><span className="delivery-pin">⌖</span><span className={`status status-${order.status}`}>{pretty(order.status)}</span></div><span className="eyebrow">ORDER #{order.id}</span><h3>{order.delivery_address}</h3><div className="order-lines">{order.items.map((x) => <span key={x.id}>{x.quantity} × {x.item_name}</span>)}</div><div className="delivery-total"><span>Collect / order value</span><b>{money(order.total_amount)}</b></div>{order.status === 'preparing' || order.status === 'confirmed' ? <button className="btn btn-primary btn-wide" onClick={() => update(order, 'out_for_delivery')}>Start delivery</button> : order.status === 'out_for_delivery' ? <button className="btn btn-primary btn-wide" onClick={() => update(order, 'delivered')}>Mark as delivered</button> : <p className="success-note">Delivery completed ✓</p>}</article>)}</div>}</section>;
}

function AdminDashboard({ token, tab, notify }) {
  const [stats, setStats] = useState(null);
  const [orders, setOrders] = useState([]);
  const [partners, setPartners] = useState([]);
  const [users, setUsers] = useState([]);
  async function load() {
    try {
      const [s, o, p, u] = await Promise.all([api('/admin/dashboard', token), api('/admin/orders', token), api('/admin/users?role=delivery', token), api('/admin/users', token)]);
      setStats(s); setOrders(o); setPartners(p); setUsers(u);
    } catch (err) { notify(err.message); }
  }
  useEffect(() => { load(); }, []);
  async function assign(orderId, deliveryId) {
    if (!deliveryId) return;
    try { await api(`/admin/orders/${orderId}/assign`, token, { method: 'PATCH', body: JSON.stringify({ delivery_partner_id: Number(deliveryId) }) }); await load(); notify(`Delivery partner assigned to order #${orderId}.`); }
    catch (err) { notify(err.message); }
  }
  if (tab === 'orders') return <section className="section-block"><div className="section-heading"><div><span className="eyebrow">PLATFORM OPERATIONS</span><h2>All orders</h2></div><button className="btn btn-outline btn-small" onClick={load}>Refresh</button></div>{orders.length === 0 ? <EmptyState title="No orders yet" text="Customer orders will appear here." /> : <div className="table-wrap"><table><thead><tr><th>Order</th><th>Customer ID</th><th>Restaurant</th><th>Status</th><th>Amount</th><th>Assign delivery</th></tr></thead><tbody>{orders.map((o) => <tr key={o.id}><td><b>#{o.id}</b><small>{new Date(o.created_at).toLocaleDateString()}</small></td><td>{o.customer_id}</td><td>{o.restaurant_id}</td><td><span className={`status status-${o.status}`}>{pretty(o.status)}</span></td><td>{money(o.total_amount)}</td><td><select value={o.delivery_partner_id || ''} onChange={(e) => assign(o.id, e.target.value)} disabled={['delivered', 'cancelled'].includes(o.status)}><option value="">Unassigned</option>{partners.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</select></td></tr>)}</tbody></table></div>}</section>;

  return <section className="section-block"><div className="section-heading"><div><span className="eyebrow">LIVE SNAPSHOT</span><h2>Platform overview</h2></div><button className="btn btn-outline btn-small" onClick={load}>Refresh data</button></div>
    <div className="stats-grid">{[['Total users', stats?.total_users, '👥'], ['Customers', stats?.total_customers, '🧑'], ['Restaurants', stats?.total_restaurants, '🍴'], ['Total orders', stats?.total_orders, '🧾'], ['Pending orders', stats?.pending_orders, '⏳'], ['Delivered', stats?.delivered_orders, '✅']].map(([label, value, icon]) => <div className="stat-card" key={label}><span>{icon}</span><small>{label}</small><b>{value ?? '—'}</b></div>)}</div>
    <div className="section-heading admin-subhead"><div><span className="eyebrow">USER DIRECTORY</span><h2>Registered users</h2></div><span className="muted">{users.length} shown</span></div>
    <div className="table-wrap"><table><thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Account ID</th></tr></thead><tbody>{users.map((u) => <tr key={u.id}><td><b>{u.name}</b></td><td>{u.email}</td><td><span className="role-mini">{u.role}</span></td><td>#{u.id}</td></tr>)}</tbody></table></div>
  </section>;
}

function EmptyState({ title, text }) {
  return <div className="empty-state"><span>🍽️</span><h3>{title}</h3><p>{text}</p></div>;
}
function pretty(value) { return String(value || '').replaceAll('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase()); }

export default App;
