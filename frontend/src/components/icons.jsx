/**
 * Line icons & Brand Logos
 */

function Icon({ children, size = 16, className = '' }) {
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {children}
    </svg>
  )
}

export function LogoIcon({ size = 28, className = '' }) {
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <rect width="32" height="32" rx="9" fill="#1D4ED8" />
      <path
        d="M10 8H20C21.1046 8 22 8.89543 22 10V22C22 23.1046 21.1046 24 20 24H10C8.89543 24 8 23.1046 8 22V10C8 8.89543 8.89543 8 10 8Z"
        stroke="white"
        strokeWidth="2"
        strokeLinejoin="round"
      />
      <path d="M12 12H18" stroke="white" strokeWidth="2" strokeLinecap="round" />
      <path d="M12 16H18" stroke="white" strokeWidth="2" strokeLinecap="round" />
      <path d="M12 20H15" stroke="white" strokeWidth="2" strokeLinecap="round" />
      <circle cx="21" cy="11" r="2.5" fill="#60A5FA" stroke="#1D4ED8" strokeWidth="1.5" />
    </svg>
  )
}

export function MenuIcon(props) {
  return (
    <Icon {...props}>
      <line x1="3" y1="12" x2="21" y2="12" />
      <line x1="3" y1="6" x2="21" y2="6" />
      <line x1="3" y1="18" x2="21" y2="18" />
    </Icon>
  )
}

export function CloseIcon(props) {
  return (
    <Icon {...props}>
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </Icon>
  )
}

export function PlusIcon(props) {
  return (
    <Icon {...props}>
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </Icon>
  )
}

export function HistoryIcon(props) {
  return (
    <Icon {...props}>
      <circle cx="12" cy="12" r="9" />
      <polyline points="12 6 12 12 16 14" />
    </Icon>
  )
}

export function TrashIcon(props) {
  return (
    <Icon {...props}>
      <path d="M4 7h16" />
      <path d="M10 11v6" />
      <path d="M14 11v6" />
      <path d="M6 7l1 13a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1l1-13" />
      <path d="M9 7V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v3" />
    </Icon>
  )
}

export function DocumentIcon(props) {
  return (
    <Icon {...props}>
      <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
      <path d="M14 3v5h5" />
      <path d="M9 13h6" />
      <path d="M9 17h4" />
    </Icon>
  )
}

export function ExternalLinkIcon(props) {
  return (
    <Icon {...props}>
      <path d="M15 3h6v6" />
      <path d="M10 14 21 3" />
      <path d="M21 14v5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5" />
    </Icon>
  )
}

export function CheckIcon(props) {
  return (
    <Icon {...props}>
      <circle cx="12" cy="12" r="9" />
      <path d="m8.5 12.4 2.4 2.4 4.6-5.2" />
    </Icon>
  )
}

export function InfoIcon(props) {
  return (
    <Icon {...props}>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 11.2V16" />
      <path d="M12 7.8h.01" />
    </Icon>
  )
}

export function WarningIcon(props) {
  return (
    <Icon {...props}>
      <path d="M10.3 4.3 2.8 17.4A2 2 0 0 0 4.5 20.4h15a2 2 0 0 0 1.7-3L13.7 4.3a2 2 0 0 0-3.4 0Z" />
      <path d="M12 9.4v4.2" />
      <path d="M12 17h.01" />
    </Icon>
  )
}

export function AlertIcon(props) {
  return (
    <Icon {...props}>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7.6V12" />
      <path d="M12 16.2h.01" />
    </Icon>
  )
}

export function SampleIcon(props) {
  return (
    <Icon {...props}>
      <path d="M12 3.5 20.5 8v8L12 20.5 3.5 16V8z" />
      <path d="M12 12 20.5 8" />
      <path d="M12 12v8.5" />
      <path d="M12 12 3.5 8" />
    </Icon>
  )
}

export function MicIcon(props) {
  return (
    <Icon {...props}>
      <rect x="9" y="3" width="6" height="11" rx="3" />
      <path d="M5 11a7 7 0 0 0 14 0" />
      <path d="M12 18v3" />
    </Icon>
  )
}

export function SendIcon(props) {
  return (
    <Icon {...props}>
      <path d="M12 19V5" />
      <path d="m5 12 7-7 7 7" />
    </Icon>
  )
}
