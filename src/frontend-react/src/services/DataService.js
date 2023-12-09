import { BASE_API_URL } from "./Common";
const axios = require('axios');

const DataService = {
    Init: function () {
        // Any application initialization logic comes here
    },
    ImageClassificationPredict: async function (formData) {
        return await axios.post(BASE_API_URL + "/predict", formData, {
            headers: {
                'Content-Type': 'multipart/form-data'
            }
        });
    },
    GetStatus: async function () {
        return await axios.get(BASE_API_URL + "/status");
    },
}

export default DataService;