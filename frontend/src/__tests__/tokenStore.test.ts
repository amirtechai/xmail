import { describe, it, expect, beforeEach } from 'vitest'
import { tokenStore } from '../lib/api'

beforeEach(() => {
  localStorage.clear()
})

describe('tokenStore', () => {
  it('returns null when no tokens stored', () => {
    expect(tokenStore.getAccess()).toBeNull()
    expect(tokenStore.getRefresh()).toBeNull()
  })

  it('stores and retrieves access and refresh tokens', () => {
    tokenStore.set('access-abc', 'refresh-xyz')
    expect(tokenStore.getAccess()).toBe('access-abc')
    expect(tokenStore.getRefresh()).toBe('refresh-xyz')
  })

  it('clears both tokens', () => {
    tokenStore.set('access-abc', 'refresh-xyz')
    tokenStore.clear()
    expect(tokenStore.getAccess()).toBeNull()
    expect(tokenStore.getRefresh()).toBeNull()
  })

  it('overwrites existing tokens on set', () => {
    tokenStore.set('old-access', 'old-refresh')
    tokenStore.set('new-access', 'new-refresh')
    expect(tokenStore.getAccess()).toBe('new-access')
    expect(tokenStore.getRefresh()).toBe('new-refresh')
  })
})
