import { FRONTEND_CORRECTIONS } from '../constants/appConfig';

export function useAutoCorrect() {
    const correct = (text) => {
        let result = text;
        let wasCorrected = false;
        Object.entries(FRONTEND_CORRECTIONS).forEach(([wrong, right]) => {
            const regex = new RegExp(`\\b${wrong}\\b`, 'gi');
            if (regex.test(result)) {
                result = result.replace(regex, right);
                wasCorrected = true;
            }
        });
        return { text: result, wasCorrected };
    };
    return { correct };
}

