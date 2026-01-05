<template>
  <div
    class="animated-emoji"
    ref="container"
    @mouseenter="playAnimation"
    @mouseleave="resetAnimation"
  >
    <!-- Fallback to static emoji if no animation available -->
    <span v-if="!hasAnimation" class="static-emoji">{{ emoji }}</span>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import lottie, { AnimationItem } from 'lottie-web'

const props = defineProps<{
  emoji: string
  state?: 'idle' | 'working' | 'excited' | 'error' | 'celebrating'
  size?: number
}>()

const container = ref<HTMLDivElement | null>(null)
const animation = ref<AnimationItem | null>(null)
const hasAnimation = ref(false)

// Map emoji characters to Lottie animation URLs
// These are hosted Lottie JSON files - can be local or CDN
const emojiAnimations: Record<string, string> = {
  // Faces
  '😀': 'https://assets2.lottiefiles.com/packages/lf20_qudhx9l0.json', // Happy face
  '😊': 'https://assets2.lottiefiles.com/packages/lf20_qudhx9l0.json',
  '😎': 'https://assets4.lottiefiles.com/packages/lf20_z9ed2ber.json', // Cool
  '🤔': 'https://assets9.lottiefiles.com/packages/lf20_k86wxpgr.json', // Thinking
  '😢': 'https://assets10.lottiefiles.com/packages/lf20_gsx4vqpj.json', // Sad
  '😂': 'https://assets9.lottiefiles.com/packages/lf20_hfwdnf8x.json', // Laughing
  '🥳': 'https://assets5.lottiefiles.com/packages/lf20_aegrfpej.json', // Party
  '😍': 'https://assets9.lottiefiles.com/packages/lf20_yr6zz3wv.json', // Heart eyes

  // Objects & Symbols
  '🔥': 'https://assets3.lottiefiles.com/packages/lf20_5ngs2ksb.json', // Fire
  '⭐': 'https://assets9.lottiefiles.com/packages/lf20_povowukx.json', // Star
  '💡': 'https://assets2.lottiefiles.com/packages/lf20_aierqrld.json', // Lightbulb idea
  '🚀': 'https://assets3.lottiefiles.com/packages/lf20_aSBWsR.json', // Rocket
  '💰': 'https://assets3.lottiefiles.com/packages/lf20_zw0djhar.json', // Money
  '❤️': 'https://assets3.lottiefiles.com/packages/lf20_sfbyyjfn.json', // Heart
  '🎯': 'https://assets3.lottiefiles.com/packages/lf20_gjmecqli.json', // Target
  '⚡': 'https://assets2.lottiefiles.com/packages/lf20_xlmz9xwm.json', // Lightning
  '🎉': 'https://assets3.lottiefiles.com/packages/lf20_aewdr2ht.json', // Party popper

  // Tech & Tools
  '💻': 'https://assets3.lottiefiles.com/packages/lf20_w51pcehl.json', // Laptop
  '📱': 'https://assets2.lottiefiles.com/packages/lf20_puciaact.json', // Phone
  '🎮': 'https://assets3.lottiefiles.com/packages/lf20_khsqjb9y.json', // Gaming
  '🔧': 'https://assets3.lottiefiles.com/packages/lf20_hgqlhqjq.json', // Wrench/tool
  '📊': 'https://assets2.lottiefiles.com/packages/lf20_rcqkfk3s.json', // Chart

  // Nature & Animals
  '🌟': 'https://assets9.lottiefiles.com/packages/lf20_povowukx.json', // Glowing star
  '🌈': 'https://assets2.lottiefiles.com/packages/lf20_xlkxtmul.json', // Rainbow
  '🌙': 'https://assets2.lottiefiles.com/packages/lf20_hscxwps9.json', // Moon
  '☀️': 'https://assets2.lottiefiles.com/packages/lf20_qspxlgog.json', // Sun

  // Activities
  '🏃': 'https://assets3.lottiefiles.com/packages/lf20_kyu0xqpv.json', // Running
  '🎵': 'https://assets2.lottiefiles.com/packages/lf20_lhwvzy7d.json', // Music
  '📚': 'https://assets2.lottiefiles.com/packages/lf20_pwohahvd.json', // Books
}

// State-based animation modifiers
const getAnimationSpeed = () => {
  switch (props.state) {
    case 'working': return 1.5
    case 'excited': return 2
    case 'error': return 0.5
    case 'celebrating': return 1.2
    default: return 1
  }
}

const loadAnimation = async () => {
  if (!container.value) return

  const animUrl = emojiAnimations[props.emoji]
  if (!animUrl) {
    hasAnimation.value = false
    return
  }

  hasAnimation.value = true

  // Destroy previous animation
  if (animation.value) {
    animation.value.destroy()
  }

  try {
    animation.value = lottie.loadAnimation({
      container: container.value,
      renderer: 'svg',
      loop: props.state !== 'celebrating',
      autoplay: true,
      path: animUrl,
    })

    animation.value.setSpeed(getAnimationSpeed())

    // For celebrating state, play once then hold
    if (props.state === 'celebrating') {
      animation.value.addEventListener('complete', () => {
        animation.value?.goToAndStop(animation.value.totalFrames - 1, true)
      })
    }
  } catch (e) {
    hasAnimation.value = false
    console.warn(`Failed to load animation for ${props.emoji}:`, e)
  }
}

const playAnimation = () => {
  if (animation.value) {
    animation.value.setSpeed(getAnimationSpeed() * 1.3) // Speed up on hover
    animation.value.play()
  }
}

const resetAnimation = () => {
  if (animation.value) {
    animation.value.setSpeed(getAnimationSpeed())
  }
}

// Watch for state changes
watch(() => props.state, () => {
  if (animation.value) {
    animation.value.setSpeed(getAnimationSpeed())
  }
})

watch(() => props.emoji, loadAnimation)

onMounted(loadAnimation)

onUnmounted(() => {
  animation.value?.destroy()
})
</script>

<style scoped>
.animated-emoji {
  width: v-bind('(props.size || 36) + "px"');
  height: v-bind('(props.size || 36) + "px"');
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: visible;
}

.animated-emoji :deep(svg) {
  width: 100% !important;
  height: 100% !important;
}

.static-emoji {
  font-size: v-bind('(props.size || 36) + "px"');
  line-height: 1;
}
</style>
