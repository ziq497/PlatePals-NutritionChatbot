import React from "react";
import { Route, Switch } from 'react-router-dom';
import Home from "../components/Home";
import Error404 from '../components/Error/404';
import ImageClassification from "../components/ImageClassification";
import ChatBot from "../components/ChatBot";

const AppRouter = (props) => {

  console.log("================================== AppRouter ======================================");

  return (
    <React.Fragment>
      <Switch>
        <Route path="/" exact component={Home} />
        <Route path="/imageclassification" exact component={ImageClassification} />
        <Route path="/chatbot" exact component={ChatBot} />
        <Route component={Error404} />
      </Switch>
    </React.Fragment>
  );
}

export default AppRouter;

