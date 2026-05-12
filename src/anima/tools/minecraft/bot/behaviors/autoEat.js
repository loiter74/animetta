/**
 * Auto Eat - automatically eats food when hungry
 */
export function setupAutoEat(bot) {
    let checkInterval = null;

    function start() {
        if (checkInterval) return;
        checkInterval = setInterval(async () => {
            if (bot.food < 6 || (bot.food < 12 && !bot.pathfinder?.isMoving())) {
                await eatFood(bot);
            }
        }, 10000); // Check every 10 seconds
    }

    function stop() {
        if (checkInterval) {
            clearInterval(checkInterval);
            checkInterval = null;
        }
    }

    return { start, stop };
}

async function eatFood(bot) {
    try {
        // Find food in inventory
        const foodItems = bot.inventory.items().filter(item => {
            if (!item || !item.name) return false;
            const name = item.name.toLowerCase();
            return name.includes('beef') || name.includes('pork') || 
                   name.includes('chicken') || name.includes('mutton') ||
                   name.includes('bread') || name.includes('apple') ||
                   name.includes('carrot') || name.includes('potato') ||
                   name.includes('cod') || name.includes('salmon');
        });

        if (foodItems.length === 0) return;

        const food = foodItems[0];
        await bot.equip(food, 'hand');
        await bot.consume();
    } catch (e) {
        // Silently ignore - we'll try again next interval
    }
}
