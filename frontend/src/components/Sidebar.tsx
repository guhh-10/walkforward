import { APP_NAME } from '../config';
import { Icon } from './Icon';

interface NavItem {
  label: string;
  icon: string;
  href?: string;
}

// Pages without an href are not built yet (see the roadmap).
const NAV_ITEMS: NavItem[] = [
  { label: 'Overview', icon: 'dashboard', href: '#overview' },
  { label: 'Transactions', icon: 'receipt_long' },
  { label: 'Forecast', icon: 'trending_up' },
  { label: 'Categories', icon: 'category' },
];

export function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand__logo">
          <Icon name="account_balance_wallet" size={22} />
        </div>
        <div className="brand__text">
          <span className="brand__name">{APP_NAME}</span>
          <span className="brand__tag">Personal Ledger</span>
        </div>
      </div>

      <nav className="nav" aria-label="Main">
        {NAV_ITEMS.map((item) =>
          item.href ? (
            <a
              key={item.label}
              className="nav__item nav__item--active"
              href={item.href}
              aria-current="page"
            >
              <Icon name={item.icon} />
              <span>{item.label}</span>
            </a>
          ) : (
            <span key={item.label} className="nav__item nav__item--disabled" aria-disabled="true">
              <Icon name={item.icon} />
              <span>{item.label}</span>
              <span className="nav__soon">Soon</span>
            </span>
          ),
        )}
      </nav>
    </aside>
  );
}
