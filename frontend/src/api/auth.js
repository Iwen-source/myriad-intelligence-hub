import service from './index'

export function login(data) {
  return service.post('/auth/login', data)
}

export function register(data) {
  return service.post('/auth/register', data)
}

export function getCurrentUser() {
  return service.get('/auth/me')
}
