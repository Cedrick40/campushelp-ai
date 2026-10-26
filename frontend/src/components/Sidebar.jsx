import { CloseIcon, HistoryIcon, PlusIcon, TrashIcon } from './icons.jsx'
import { formatHistoryTime } from '../format.js'

export default function Sidebar({
  id,
  isOpen,
  onClose,
  history,
  onSelect,
  onDelete,
  onClear,
  onNewChat,
  user,
  accountName,
  onLogout,
  error,
}) {
  const initial = (accountName || user?.email || '?')[0].toUpperCase()

  return (
    <>
      {isOpen ? (
        <div
          className="sidebarOverlay"
          onClick={onClose}
          aria-hidden="true"
        />
      ) : null}

      <aside
        id={id}
        className={`sidebar ${isOpen ? 'sidebar--open' : ''}`}
        aria-label="Saved chats"
        aria-hidden={!isOpen}
        inert={!isOpen}
      >
        <div className="sidebar__header">
          <button className="sidebar__newChat" type="button" onClick={onNewChat}>
            <PlusIcon size={16} />
            <span>New chat</span>
          </button>
          <button
            className="iconButton"
            type="button"
            onClick={onClose}
            aria-label="Close sidebar"
          >
            <CloseIcon size={18} />
          </button>
        </div>

        <div className="sidebar__content">
          <div className="sidebar__sectionRow">
            <div className="sidebar__sectionTitle">
              <HistoryIcon size={14} />
              <span>Saved chats</span>
            </div>
            {history.length > 0 ? (
              <button
                className="sidebar__clear"
                type="button"
                onClick={onClear}
              >
                Clear
              </button>
            ) : null}
          </div>

          {error ? (
            <p className="sidebar__error" role="alert">
              {error}
            </p>
          ) : null}

          {history.length === 0 ? (
            <p className="sidebar__empty">
              No saved chats yet. Ask a question while logged in and it will
              appear here.
            </p>
          ) : (
            <ul className="sidebar__list">
              {history.map((item) => (
                <li key={item.id} className="sidebar__item">
                  <button
                    className="sidebar__itemButton"
                    type="button"
                    onClick={() => onSelect(item)}
                    title={item.question}
                  >
                    <span className="sidebar__itemTitle">{item.title}</span>
                    <span className="sidebar__itemTime">
                      {formatHistoryTime(item.updatedAt || item.createdAt) ||
                        'Saved'}
                    </span>
                  </button>
                  <button
                    className="sidebar__itemDelete"
                    type="button"
                    onClick={() => onDelete(item)}
                    aria-label={`Delete saved chat: ${item.title}`}
                  >
                    <TrashIcon size={14} />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="sidebar__footer">
          <div className="sidebar__userInfo">
            <span className="userAvatar" aria-hidden="true">
              {initial}
            </span>
            <div className="sidebar__userDetails">
              <span className="sidebar__userName">{accountName}</span>
              <span className="sidebar__userEmail">{user?.email}</span>
            </div>
          </div>
          <button
            className="authButton authButton--text sidebar__logout"
            type="button"
            onClick={onLogout}
          >
            Log out
          </button>
        </div>
      </aside>
    </>
  )
}
