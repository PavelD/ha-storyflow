class StoryFlowCard extends HTMLElement {
    set hass(hass) {
        // TODO: proper display
    }

    getCardSize() {
        return 3;
    }
}

customElements.define('storyflow-card', StoryFlowCard);
