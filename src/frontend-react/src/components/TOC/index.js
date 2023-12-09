import React, { useEffect } from 'react';
import { withStyles } from '@material-ui/core';
import Typography from '@material-ui/core/Typography';
import List from '@material-ui/core/List';
import ListItem from '@material-ui/core/ListItem';
import ListItemIcon from '@material-ui/core/ListItemIcon';
import ListItemText from '@material-ui/core/ListItemText';
import Divider from '@material-ui/core/Divider';
import { Link } from 'react-router-dom';
import { Icon } from '@material-ui/core';
import styles from './styles';


const TOC = (props) => {
    const { classes } = props;

    console.log("================================== TOC ======================================");


    // Component States


    // Setup Component
    useEffect(() => {

    }, []);

    // Handlers



    return (
        <div className={classes.root}>
            <main className={classes.main}>
                <Typography variant="h5" gutterBottom>Table of Content</Typography>
                <List>
                    <ListItem button component={Link} to="/">
                        <ListItemIcon><Icon>home</Icon></ListItemIcon>
                        <ListItemText primary='Home' />
                    </ListItem>
                </List>
                <Divider />
                <List>
                    <ListItem button component={Link} to="/imageclassification">
                        <ListItemIcon><Icon>image</Icon></ListItemIcon>
                        <ListItemIcon><Icon>smart_toy</Icon></ListItemIcon>
                        <ListItemText primary='Upload Image / Chatbot' />
                    </ListItem>
                </List>
            </main>
        </div>
    );
};

export default withStyles(styles)(TOC);