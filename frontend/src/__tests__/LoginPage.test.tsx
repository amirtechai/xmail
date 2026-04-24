import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import LoginPage from '../pages/LoginPage'

// Mock useAuth store
const mockLogin = vi.fn()
const mockCompleteTOTP = vi.fn()

vi.mock('../lib/auth', () => ({
  useAuth: (selector: (s: unknown) => unknown) => {
    const state = {
      login: mockLogin,
      completeTOTP: mockCompleteTOTP,
      loading: false,
    }
    return selector(state)
  },
}))

// Mock useNavigate
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => mockNavigate }
})

function renderLogin() {
  return render(
    <MemoryRouter>
      <LoginPage />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('LoginPage', () => {
  it('renders sign-in form', () => {
    renderLogin()
    expect(screen.getByRole('heading', { name: 'Sign in' })).toBeInTheDocument()
    expect(screen.getByPlaceholderText('admin@priceonn.com')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('••••••••')).toBeInTheDocument()
  })

  it('navigates to dashboard on successful login', async () => {
    mockLogin.mockResolvedValueOnce({ requires_totp: false })
    renderLogin()

    fireEvent.change(screen.getByPlaceholderText('admin@priceonn.com'), {
      target: { value: 'admin@priceonn.com' },
    })
    fireEvent.change(screen.getByPlaceholderText('••••••••'), {
      target: { value: 'password' },
    })
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/dashboard', { replace: true })
    })
  })

  it('shows TOTP step when requires_totp is true', async () => {
    mockLogin.mockResolvedValueOnce({ requires_totp: true, totp_token: 'challenge-token' })
    renderLogin()

    fireEvent.change(screen.getByPlaceholderText('admin@priceonn.com'), {
      target: { value: 'admin@priceonn.com' },
    })
    fireEvent.change(screen.getByPlaceholderText('••••••••'), {
      target: { value: 'password' },
    })
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => {
      expect(screen.getByText('Two-Factor Auth')).toBeInTheDocument()
    })
  })

  it('shows error on login failure', async () => {
    mockLogin.mockRejectedValueOnce(new Error('Invalid credentials'))
    renderLogin()

    fireEvent.change(screen.getByPlaceholderText('admin@priceonn.com'), {
      target: { value: 'bad@example.com' },
    })
    fireEvent.change(screen.getByPlaceholderText('••••••••'), {
      target: { value: 'wrong' },
    })
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => {
      expect(screen.getByText('Invalid credentials. Please try again.')).toBeInTheDocument()
    })
  })

  it('back button returns to login form from TOTP step', async () => {
    mockLogin.mockResolvedValueOnce({ requires_totp: true, totp_token: 'tok' })
    renderLogin()

    fireEvent.change(screen.getByPlaceholderText('admin@priceonn.com'), {
      target: { value: 'user@example.com' },
    })
    fireEvent.change(screen.getByPlaceholderText('••••••••'), {
      target: { value: 'pass' },
    })
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => screen.getByText('Two-Factor Auth'))
    fireEvent.click(screen.getByText('← Back to login'))
    expect(screen.getByRole('heading', { name: 'Sign in' })).toBeInTheDocument()
  })
})
