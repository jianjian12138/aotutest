import request from '@/utils/request'

export function executeAgentAction(data) {
  return request({
    url: '/api/assistant/agent/execute/',
    method: 'post',
    data
  })
}
