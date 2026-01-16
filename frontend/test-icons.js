// 测试Element Plus Icons Vue中可用的图标
import * as Icons from '@element-plus/icons-vue';

// 打印所有图标名称
console.log('Available icons:', Object.keys(Icons).filter(name => 
  name.toLowerCase().includes('full') || name.toLowerCase().includes('screen')
));

// 特别检查全屏相关图标
console.log('Fullscreen related icons:', {
  hasFullscreen: 'Fullscreen' in Icons,
  hasFullscreenExit: 'FullscreenExit' in Icons,
  hasFullScreen: 'FullScreen' in Icons,
  hasFullScreenExit: 'FullScreenExit' in Icons,
  hasMaximize: 'Maximize' in Icons,
  hasMinimize: 'Minimize' in Icons
});