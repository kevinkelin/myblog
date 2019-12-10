var config = {
    model: {
        jsonPath: '../blackcat/hijiki.model.json',
    },
    display: {
        superSample: 1,
        width: 245,
        height: 245,
        position: 'right',
        hOffset: 100,
        vOffset: 0,
    },
    mobile: {
        show: false,
        scale: 1,
        motion: false,
    },
    react: {
        opacityDefault: 1,
        opacityOnHover: 0.75
    }
};
L2Dwidget.init(config);